import time

from itertools import chain
from queue import PriorityQueue, Empty
from threading import Thread

from .common import join_all
from .errors import ConnectionClosed
from .logging import get_logger
from .middleware import Middleware


class Worker:
    """Consumes messages off of all declared queues on a worker and
    distributes those messages to individual worker threads so that
    actors may process them.

    There should be at most one worker instance per process.

    Parameters:
      broker(Broker)
      worker_timeout(int): The number of milliseconds workers should
        wake up after if the queue is idle.
      worker_threads(int): The number of worker threads to spawn.
    """

    def __init__(self, broker, *, worker_timeout=5000, worker_threads=8):
        self.broker = broker
        self.consumers = {}
        self.workers = []
        self.work_prefetch = worker_threads
        self.work_queue = PriorityQueue()
        self.worker_timeout = worker_timeout
        self.worker_threads = worker_threads
        self.logger = get_logger(__name__, type(self))

    def add_consumer(self, queue_name):
        if queue_name not in self.consumers:
            consumer = _ConsumerThread(self.broker, self.work_queue, self.work_prefetch, queue_name)
            consumer.start()

            self.consumers[queue_name] = consumer

    def add_worker(self):
        worker = _WorkerThread(self.broker, self.work_queue, self.worker_timeout)
        worker.start()
        self.workers.append(worker)

    def start(self):
        self.broker.emit_before("worker_boot", self)

        worker_middleware = _WorkerMiddleware(self)
        self.broker.add_middleware(worker_middleware)
        for _ in range(self.worker_threads):
            self.add_worker()

        self.broker.emit_after("worker_boot", self)

    def stop(self, timeout=5000):
        self.broker.emit_before("worker_shutdown", self)
        self.logger.info("Shutting down...")
        self.logger.debug("Stopping consumers and workers...")
        for thread in chain(self.consumers.values(), self.workers):
            thread.stop()

        self.logger.debug("Consumers and workers stopped.")
        self.logger.debug("Waiting for consumers and workers to stop...")
        join_all(chain(self.consumers.values(), self.workers), timeout)

        self.logger.debug("Consumers and workers joined.")
        self.logger.debug("Closing channels...")
        for thread in self.consumers.values():
            thread.close()

        self.logger.debug("Channels closed.")
        self.broker.emit_after("worker_shutdown", self)
        self.logger.info("Worker has been shut down.")


class _WorkerMiddleware(Middleware):
    def __init__(self, worker):
        self.worker = worker

    def after_declare_queue(self, broker, queue_name):
        self.worker.add_consumer(queue_name)


class _ConsumerThread(Thread):
    def __init__(self, broker, work_queue, work_prefetch, queue_name):
        super().__init__(daemon=True)

        self.running = False
        self.broker = broker
        self.consumer = None
        self.queue_name = queue_name
        self.work_prefetch = work_prefetch
        self.work_queue = work_queue
        self.logger = get_logger(__name__, f"ConsumerThread({queue_name})")

    def run(self, attempts=0):
        try:
            self.logger.debug("Running consumer thread...")
            self.consumer = self.broker.consume(
                queue_name=self.queue_name,
                prefetch=self.work_prefetch,
            )
            self.running = True

            # Reset the attempts counter since we presumably got a
            # working connection.
            attempts = 0
            for message in self.consumer:
                if message is not None:
                    actor = self.broker.get_actor(message.actor_name)
                    self.logger.debug("Pushing message %r onto work queue.", message.message_id)
                    self.work_queue.put((actor.priority, message))

                if not self.running:
                    break
        except ConnectionClosed:
            delay = min(0.5 * attempts ** 2, 10)
            self.logger.warning("Connection error encountered. Waiting for %.02f before restarting...", delay)

            time.sleep(delay)
            return self.run(attempts=attempts + 1)

        self.logger.debug("Consumer thread stopped.")

    def stop(self):
        self.logger.debug("Stopping consumer thread...")
        self.running = False

    def close(self):
        if self.consumer:
            self.logger.debug("Closing consumer...")
            self.consumer.close()


class _WorkerThread(Thread):
    def __init__(self, broker, work_queue, worker_timeout):
        super().__init__(daemon=True)

        self.running = False
        self.broker = broker
        self.work_queue = work_queue
        self.worker_timeout = worker_timeout
        self.logger = get_logger(__name__, "WorkerThread")

    def run(self):
        self.logger.debug("Running worker thread...")
        self.running = True
        while self.running:
            try:
                self.logger.debug("Waiting for message...")
                _, message = self.work_queue.get(timeout=self.worker_timeout / 1000)
                self.logger.debug("Received message %s with id %r.", message, message.message_id)
                self.broker.process_message(message)
                self.work_queue.task_done()

            except Empty:
                self.logger.debug("Reached wait timeout...")

            except BaseException:
                self.work_queue.task_done()
                self.logger.warning(
                    "An unhandled exception occurred while processing message %r.",
                    message.message_id, exc_info=True,
                )

        self.logger.debug("Worker thread stopped.")

    def stop(self):
        self.logger.debug("Stopping worker thread...")
        self.running = False
