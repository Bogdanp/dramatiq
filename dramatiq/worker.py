import time

from itertools import chain
from queue import Empty, PriorityQueue, Queue
from threading import Thread

from .common import current_millis, iter_queue, join_all
from .errors import ConnectionClosed
from .logging import get_logger
from .middleware import Middleware


class Worker:
    """Workers consume messages off of all declared queues and
    distribute those messages to individual worker threads for
    processing.  Workers don't block the current thread so it's
    up to the caller to keep it alive.

    Don't run more than one Worker per process.

    Parameters:
      broker(Broker)
      worker_timeout(int): The number of milliseconds workers should
        wake up after if the queue is idle.
      worker_threads(int): The number of worker threads to spawn.
    """

    def __init__(self, broker, *, worker_timeout=1000, worker_threads=8):
        self.logger = get_logger(__name__, type(self))
        self.broker = broker

        self.consumers = {}
        self.queue_prefetch = worker_threads * 100
        self.delay_prefetch = worker_threads * 1000  # TODO: Make this configurable.
        self.delay_queue = PriorityQueue()

        self.workers = []
        self.work_queue = PriorityQueue()
        self.worker_timeout = worker_timeout
        self.worker_threads = worker_threads

    def start(self):
        """Initialize the worker boot sequence and start up all the
        worker threads.
        """
        self.broker.emit_before("worker_boot", self)

        worker_middleware = _WorkerMiddleware(self)
        self.broker.add_middleware(worker_middleware)
        for _ in range(self.worker_threads):
            self._add_worker()

        self.broker.emit_after("worker_boot", self)

    def stop(self, timeout=60000):
        """Gracefully stop the Worker and all of its consumers and
        workers.

        Parameters:
          timeout(int): The number of milliseconds to wait for
            everything to shut down.
        """
        self.broker.emit_before("worker_shutdown", self)
        self.logger.info("Shutting down...")
        self.logger.debug("Stopping consumers and workers...")
        for thread in chain(self.consumers.values(), self.workers):
            thread.stop()

        join_all(chain(self.workers, self.consumers.values()), timeout)
        self.logger.debug("Consumers and workers stopped.")
        self.logger.debug("Closing consumers...")
        for consumer in self.consumers.values():
            consumer.close()

        self.logger.debug("Consumers closed.")
        self.broker.emit_after("worker_shutdown", self)
        self.logger.info("Worker has been shut down.")

    def join(self):
        """Wait for this worker to complete its work in progress.
        This method is useful when testing code.
        """
        while True:
            self.delay_queue.join()
            self.work_queue.join()

            # If nothing got put on the delay queue while we were
            # joining on the work queue then it shoud be safe to exit.
            # This could still miss stuff but the chances are slim.
            if self.delay_queue.qsize() == 0:
                break

    def _add_consumer(self, queue_name, *, delay=False):
        if queue_name in self.consumers:
            return

        consumer = self.consumers[queue_name] = _ConsumerThread(
            broker=self.broker,
            queue_name=queue_name,
            prefetch=self.delay_prefetch if delay else self.queue_prefetch,
            work_queue=self.work_queue,
            delay_queue=self.delay_queue,
        )
        consumer.start()

    def _add_worker(self):
        worker = _WorkerThread(
            broker=self.broker,
            consumers=self.consumers,
            work_queue=self.work_queue,
            worker_timeout=self.worker_timeout
        )
        worker.start()
        self.workers.append(worker)


class _WorkerMiddleware(Middleware):
    def __init__(self, worker):
        self.logger = get_logger(__name__, type(self))
        self.worker = worker

    def after_declare_queue(self, broker, queue_name):
        self.logger.debug("Adding consumer for queue %r.", queue_name)
        self.worker._add_consumer(queue_name)

    def after_declare_delay_queue(self, broker, queue_name):
        self.logger.debug("Adding consumer for delay queue %r.", queue_name)
        self.worker._add_consumer(queue_name, delay=True)


class _ConsumerThread(Thread):
    def __init__(self, *, broker, queue_name, prefetch, work_queue, delay_queue):
        super().__init__(daemon=True)

        self.logger = get_logger(__name__, f"ConsumerThread({queue_name})")
        self.running = False
        self.consumer = None
        self.broker = broker
        self.prefetch = prefetch
        self.queue_name = queue_name
        self.work_queue = work_queue
        self.delay_queue = delay_queue
        self.acks_queue = Queue()

    def run(self, attempts=0):
        try:
            self.logger.debug("Running consumer thread...")
            self.running = True
            self.consumer = self.broker.consume(
                queue_name=self.queue_name,
                prefetch=self.prefetch,

                # We're being a little piggy here.  We don't have a
                # good way to signal the consumer to stop idling when
                # we get ack requests, so we have to have a low idle
                # timeout instead.
                timeout=20,
            )

            # Reset the attempts counter since we presumably got a
            # working connection.
            attempts = 0
            for message in self.consumer:
                if message is not None:
                    self.handle_message(message)

                self.handle_idle()
                if not self.running:
                    break
        except ConnectionClosed:
            if self.running:
                delay = min(0.5 * attempts ** 2, 10)
                self.logger.warning("Connection error encountered. Waiting for %.02f before restarting...", delay)

                time.sleep(delay)
                return self.run(attempts=attempts + 1)

        self.logger.debug("Consumer thread stopped.")

    def handle_idle(self):
        for message in iter_queue(self.acks_queue):
            if message.failed:
                self.logger.debug("Rejecting message %r.", message.message_id)
                self.broker.emit_before("reject", message)
                message.reject()
                self.broker.emit_after("reject", message)

            else:
                self.logger.debug("Acknowledging message %r.", message.message_id)
                self.broker.emit_before("acknowledge", message)
                message.acknowledge()
                self.broker.emit_after("acknowledge", message)

            self.acks_queue.task_done()

        for eta, message in iter_queue(self.delay_queue):
            if eta > current_millis():
                self.delay_queue.put((eta, message))
                self.delay_queue.task_done()
                return

            actor = self.broker.get_actor(message.actor_name)
            self.logger.debug("Pushing message %r onto work queue.", message.message_id)
            self.work_queue.put((actor.priority, message))
            self.delay_queue.task_done()

    def handle_message(self, message):
        """Handle a message received off of the underlying consumer.
        If the message has an eta, delay it.  Otherwise, put it on the
        work queue.
        """
        if "eta" in message.options:
            self.logger.debug("Pushing message %r onto delay queue.", message.message_id)
            self.broker.emit_before("delay_message", message)
            self.delay_queue.put((message.options.get("eta", 0), message))

        else:
            actor = self.broker.get_actor(message.actor_name)
            self.logger.debug("Pushing message %r onto work queue.", message.message_id)
            self.work_queue.put((actor.priority, message))

    def post_process_message(self, message):
        """Called by worker threads whenever they're done processing
        individual messages, signaling that each message is ready to
        be acked or rejected.
        """
        self.acks_queue.put(message)

    def stop(self):
        """Initiate the ConsumerThread shutdown sequence.

        Code calling this method should then join on the thread and
        wait for it to finish shutting down.
        """
        self.logger.debug("Stopping consumer thread...")
        self.running = False

    def close(self):
        """Close this consumer thread and its underlying connection.
        """
        self.consumer.close()


class _WorkerThread(Thread):
    """WorkerThreads process incoming messages off of the work queue
    on a loop.  By themselves, they don't do any sort of network IO.

    Parameters:
      broker(Broker)
      consumers(dict[str, _ConsumerThread])
      work_queue(Queue)
      worker_timeout(int)
    """

    def __init__(self, *, broker, consumers, work_queue, worker_timeout):
        super().__init__(daemon=True)

        self.logger = get_logger(__name__, "WorkerThread")
        self.running = False
        self.broker = broker
        self.consumers = consumers
        self.work_queue = work_queue
        self.worker_timeout = worker_timeout

    def run(self):
        self.logger.debug("Running worker thread...")
        self.running = True
        while self.running:
            try:
                _, message = self.work_queue.get(timeout=self.worker_timeout / 1000)
                self.process_message(message)
            except Empty:
                continue
        self.logger.debug("Worker thread stopped.")

    def process_message(self, message):
        """Process a message pulled off of the work queue then push it
        back to its associated consumer for post processing.

        Parameters:
          message(MessageProxy)
        """
        try:
            self.logger.debug("Received message %s with id %r.", message, message.message_id)
            self.broker.emit_before("process_message", message)

            res = None
            if not message.failed:
                actor = self.broker.get_actor(message.actor_name)
                res = actor(*message.args, **message.kwargs)

            self.broker.emit_after("process_message", message, result=res)

        except BaseException as e:
            self.logger.warning("Failed to process message %r with unhandled exception.", message, exc_info=True)
            self.broker.emit_after("process_message", message, exception=e)

        finally:
            # NOTE: There is no race here as any message that was
            # processed must have come off of a consumer.  Therefore,
            # there has to be a consumer for that message's queue so
            # this is safe.  Probably.
            self.consumers[message.queue_name].post_process_message(message)
            self.work_queue.task_done()

    def stop(self):
        """Initiate the WorkerThread shutdown process.

        Code calling this method should then join on the thread and
        wait for it to finish shutting down.
        """
        self.logger.debug("Stopping worker thread...")
        self.running = False
