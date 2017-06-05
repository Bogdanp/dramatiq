import time

from itertools import chain
from queue import PriorityQueue, Empty
from threading import Thread

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
      work_factor(int): The max number of messages to load into memory
        per worker thread pending processing.
    """

    def __init__(self, broker, *, worker_timeout=5000, worker_threads=8, work_factor=10000):
        self.broker = broker
        self.consumers = {}
        self.workers = []
        self.work_queue = PriorityQueue(maxsize=work_factor * worker_threads)
        self.worker_timeout = worker_timeout
        self.worker_threads = worker_threads
        self.logger = get_logger(__name__, type(self))

    def add_consumer(self, queue_name):
        if queue_name not in self.consumers:
            consumer = _ConsumerThread(self.broker, self.work_queue, queue_name)
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

    def stop(self, timeout=5):
        self.broker.emit_before("worker_shutdown", self)
        self.logger.info("Shutting down...")
        for thread in chain(self.consumers.values(), self.workers):
            thread.stop()

        for thread in chain(self.consumers.values(), self.workers):
            thread.join(timeout=timeout)

        self.broker.emit_after("worker_shutdown", self)


class _WorkerMiddleware(Middleware):
    def __init__(self, worker):
        self.worker = worker

    def after_declare_queue(self, broker, queue_name):
        self.worker.add_consumer(queue_name)


class _ConsumerThread(Thread):
    def __init__(self, broker, work_queue, queue_name):
        super().__init__(daemon=True)

        self.running = False
        self.broker = broker
        self.queue_name = queue_name
        self.work_queue = work_queue
        self.logger = get_logger(__name__, f"ConsumerThread({queue_name})")

    def run(self, attempts=0):
        try:
            self.logger.debug("Running consumer thread...")
            self.consumer = self.broker.consume(self.queue_name)
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

        self.logger.debug("Closing consumer...")
        self.consumer.close()
        self.logger.debug("Consumer thread stopped.")

    def stop(self):
        self.logger.debug("Stopping consumer thread...")
        self.running = False


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

            except Empty:
                self.logger.debug("Reached wait timeout...")

            except Exception:
                self.logger.warning(
                    "An unhandled exception occurred while processing message %r.",
                    message.message_id, exc_info=True,
                )

        self.logger.debug("Worker thread stopped.")

    def stop(self):
        self.logger.debug("Stopping worker thread...")
        self.running = False
