import logging
import uuid

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

    def __init__(self, broker, worker_threads=8, get_timeout=30):
        self.broker = broker
        self.work_queue = Queue()
        self.get_timeout = get_timeout

        self.consumers = []
        for queue_name in broker.get_declared_queues():
            self.add_consumer(queue_name)
        self.broker.add_middleware(self)

        self.workers = []
        for _ in range(worker_threads):
            self.add_worker()

    def add_consumer(self, queue_name):
        consumer = _Consumer(self.broker, self.work_queue, queue_name)
        consumer.start()
        self.consumers.append(consumer)

    def add_worker(self):
        worker = _Worker(self.broker, self.work_queue, self.get_timeout)
        worker.start()
        self.workers.append(worker)

    def after_declare_queue(self, queue_name):
        self.add_consumer(queue_name)

    def stop(self, timeout=5):
        for thread in chain(self.consumers, self.workers):
            thread.stop()

        for thread in chain(self.consumers, self.workers):
            thread.join(timeout=timeout)

    def __str__(self):
        return f"Worker({self.broker!r})"


class _Consumer(Thread):
    def __init__(self, broker, work_queue, queue_name):
        super().__init__(daemon=True)

        self.broker = broker
        self.consumer = broker.get_consumer(queue_name, self.on_message)
        self.queue_name = queue_name
        self.work_queue = work_queue
        self.logger = logging.getLogger(f"Consumer({queue_name!r})")

    def on_message(self, message, ack_id):
        self.logger.debug("Received message %r with ack id %r.", message, ack_id)
        self.work_queue.put((message, ack_id))

    def run(self):
        self.logger.info("Starting...")
        self.consumer.start()

    def stop(self):
        self.logger.info("Stopping...")
        self.consumer.stop()
        self.logger.info("Stopped.")


class _Worker(Thread):
    def __init__(self, broker, work_queue, get_timeout):
        super().__init__(daemon=True)

        self.running = True
        self.broker = broker
        self.work_queue = work_queue
        self.get_timeout = get_timeout
        self.logger = logging.getLogger(f"Worker#{uuid.uuid4()}")

    def run(self):
        self.logger.info("Running...")
        while self.running:
            try:
                self.logger.debug("Waiting for message...")
                message, ack_id = self.work_queue.get(timeout=self.get_timeout)
                self.broker.process_message(message, ack_id)
            except Empty:
                pass

    def stop(self):
        self.logger.info("Shutting down...")
        self.running = False
