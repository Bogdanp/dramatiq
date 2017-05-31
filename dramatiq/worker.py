import logging

from itertools import chain
from queue import Queue, Empty
from threading import Thread

from .middleware import Middleware


class Worker(Middleware):
    """Consumes messages off of all declared queues on a worker and
    distributes those messages to individual worker threads so that
    actors may process them.

    There should be at most one worker instance per process.
    """

    def __init__(self, broker, worker_threads=8, wait_timeout=5):
        self.broker = broker
        self.wait_timeout = wait_timeout
        self.work_queue = Queue()
        self.worker_threads = worker_threads

    def add_consumer(self, queue_name):
        consumer = _Consumer(self.broker, self.work_queue, queue_name)
        consumer.start()
        self.consumers.append(consumer)

    def add_worker(self):
        worker = _Worker(self.broker, self.work_queue, self.wait_timeout)
        worker.start()
        self.workers.append(worker)

    def after_declare_queue(self, queue_name):
        self.add_consumer(queue_name)

    def start(self):
        self.consumers = []
        for queue_name in self.broker.get_declared_queues():
            self.add_consumer(queue_name)
        self.broker.add_middleware(self)

        self.workers = []
        for _ in range(self.worker_threads):
            self.add_worker()

    def stop(self, timeout=5):
        for thread in chain(self.consumers, self.workers):
            thread.stop()

        for thread in chain(self.consumers, self.workers):
            thread.join(timeout=timeout)


class _Consumer(Thread):
    def __init__(self, broker, work_queue, queue_name):
        super().__init__(daemon=True)

        self.broker = broker
        self.consumer = broker.get_consumer(queue_name, self.on_message)
        self.queue_name = queue_name
        self.work_queue = work_queue
        self.logger = logging.getLogger(f"Consumer({queue_name!r})")

    def on_message(self, message, ack_id):
        self.logger.debug("Pushing message %r onto work queue.", message.message_id)
        self.work_queue.put((message, ack_id))

    def run(self):
        self.logger.info("Starting...")
        self.consumer.start()
        self.logger.info("Stopped.")

    def stop(self):
        self.logger.info("Stopping consumer %r...", self)
        self.consumer.stop()


class _Worker(Thread):
    def __init__(self, broker, work_queue, wait_timeout):
        super().__init__(daemon=True)

        self.running = True
        self.broker = broker
        self.work_queue = work_queue
        self.wait_timeout = wait_timeout
        self.logger = logging.getLogger("Worker")

    def run(self):
        self.logger.info("Running...")
        while self.running:
            try:
                self.logger.debug("Waiting for message...")
                message, ack_id = self.work_queue.get(timeout=self.wait_timeout)
                self.logger.debug("Received message %s with id %r.", message, message.message_id)
                self.broker.process_message(message, ack_id)

            except Empty:
                self.logger.debug("Reached wait timeout...")

            except Exception:
                self.logger.warning("An unhandled exception occurred while processing a message.", exc_info=True)

        self.logger.info("Stopped.")

    def stop(self):
        self.logger.info("Stopping worker %r...", self)
        self.running = False
