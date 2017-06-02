import logging
import time

from itertools import chain
from queue import Queue, Empty
from threading import Thread

from .errors import ConnectionClosed
from .middleware import Middleware


class Worker:
    """Consumes messages off of all declared queues on a worker and
    distributes those messages to individual worker threads so that
    actors may process them.

    There should be at most one worker instance per process.
    """

    def __init__(self, broker, worker_timeout=5, worker_threads=8):
        self.broker = broker
        self.consumers = {}
        self.workers = []
        self.work_queue = Queue()
        self.worker_timeout = worker_timeout
        self.worker_threads = worker_threads
        self.logger = logging.getLogger("WorkerProcess")

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
        worker_middleware = _WorkerMiddleware(self)
        self.broker.add_middleware(worker_middleware)
        for _ in range(self.worker_threads):
            self.add_worker()

    def stop(self, timeout=5):
        self.logger.info("Shutting down...")
        for thread in chain(self.consumers.values(), self.workers):
            thread.stop()

        for thread in chain(self.consumers.values(), self.workers):
            thread.join(timeout=timeout)


class _WorkerMiddleware(Middleware):
    def __init__(self, worker):
        self.worker = worker

    def after_declare_queue(self, queue_name):
        self.worker.add_consumer(queue_name)


class _ConsumerThread(Thread):
    def __init__(self, broker, work_queue, queue_name):
        super().__init__(daemon=True)

        self.running = True
        self.broker = broker
        self.queue_name = queue_name
        self.work_queue = work_queue
        self.logger = logging.getLogger(f"ConsumerThread({queue_name})")

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
                    self.logger.debug("Pushing message %r onto work queue.", message.message_id)
                    self.work_queue.put(message)

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

        self.running = True
        self.broker = broker
        self.work_queue = work_queue
        self.worker_timeout = worker_timeout
        self.logger = logging.getLogger("WorkerThread")

    def run(self):
        self.logger.debug("Running worker thread...")
        while self.running:
            try:
                self.logger.debug("Waiting for message...")
                message = self.work_queue.get(timeout=self.worker_timeout)
                self.logger.debug("Received message %s with id %r.", message, message.message_id)
                self.broker.process_message(message)

            except Empty:
                self.logger.debug("Reached wait timeout...")

            except Exception:
                self.logger.warning("An unhandled exception occurred while processing a message.", exc_debug=True)

        self.logger.debug("Worker thread stopped.")

    def stop(self):
        self.logger.debug("Stopping worker thread...")
        self.running = False
