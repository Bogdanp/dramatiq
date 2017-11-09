import time

from collections import defaultdict
from itertools import chain
from queue import Empty, PriorityQueue, Queue
from threading import Event, Thread

from .common import compute_backoff, current_millis, iter_queue, join_all, q_name
from .errors import ActorNotFound, ConnectionError
from .logging import get_logger
from .middleware import Middleware, SkipMessage


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
        # Load a small factor more messages than there are workers to
        # avoid waiting on network IO as much as possible.  The factor
        # must be small so we don't starve other workers out.
        self.queue_prefetch = min(worker_threads * 2, 65535)
        # Load a large factor more delay messages than there are
        # workers as those messages could have far-future etas.
        self.delay_prefetch = min(worker_threads * 1000, 65535)

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

    def pause(self):
        """Pauses all the worker threads.
        """
        for worker in self.workers:
            worker.pause()

        for worker in self.workers:
            worker.paused_event.wait()

    def resume(self):
        """Resumes all the worker threads.
        """
        for worker in self.workers:
            worker.resume()

    def stop(self, timeout=600000):
        """Gracefully stop the Worker and all of its consumers and
        workers.

        Parameters:
          timeout(int): The number of milliseconds to wait for
            everything to shut down.
        """
        self.broker.emit_before("worker_shutdown", self)
        self.logger.info("Shutting down...")
        self.logger.debug("Stopping consumers and workers...")
        for thread in chain(self.workers, self.consumers.values()):
            thread.stop()

        join_all(chain(self.workers, self.consumers.values()), timeout)
        self.logger.debug("Consumers and workers stopped.")

        self.logger.debug("Requeueing in-memory messages...")
        messages_by_queue = defaultdict(list)
        for _, message in iter_queue(self.work_queue):
            messages_by_queue[message.queue_name].append(message)

        for queue_name, messages in messages_by_queue.items():
            try:
                self.consumers[queue_name].requeue_messages(messages)
            except ConnectionError as e:
                self.logger.warning("Failed to requeue messages on queue %r.", queue_name, exc_info=True)
        self.logger.debug("Done requeueing in-progress messages.")

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
            for consumer in self.consumers.values():
                consumer.delay_queue.join()

            self.work_queue.join()

            # If nothing got put on the delay queues while we were
            # joining on the work queue then it shoud be safe to exit.
            # This could still miss stuff but the chances are slim.
            for consumer in self.consumers.values():
                if consumer.delay_queue.qsize() > 0:
                    break
            else:
                return

    def _add_consumer(self, queue_name, *, delay=False):
        if queue_name in self.consumers:
            return

        consumer = self.consumers[queue_name] = _ConsumerThread(
            broker=self.broker,
            queue_name=queue_name,
            prefetch=self.delay_prefetch if delay else self.queue_prefetch,
            work_queue=self.work_queue,
            worker_timeout=self.worker_timeout,
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
    def __init__(self, *, broker, queue_name, prefetch, work_queue, worker_timeout):
        super().__init__(daemon=True)

        self.logger = get_logger(__name__, f"ConsumerThread({queue_name})")
        self.running = False
        self.consumer = None
        self.broker = broker
        self.prefetch = prefetch
        self.queue_name = queue_name
        self.work_queue = work_queue
        self.worker_timeout = worker_timeout
        self.delay_queue = PriorityQueue()
        self.acks_queue = Queue()

    def run(self, attempts=0):
        try:
            self.logger.debug("Running consumer thread...")
            self.running = True
            self.consumer = self.broker.consume(
                queue_name=self.queue_name,
                prefetch=self.prefetch,
                timeout=self.worker_timeout,
            )

            # Reset the attempts counter since we presumably got a
            # working connection.
            attempts = 0
            for message in self.consumer:
                if message is not None:
                    self.handle_message(message)

                self.handle_acks()
                self.handle_delayed_messages()
                if not self.running:
                    break

        except ConnectionError:
            self.logger.error("Consumer encountered a connection error.", exc_info=True)
            # Acking is unsafe when the connection is abruptly closed
            # so we must clear the queue.  All brokers have at-least
            # once semantics so this is a safe operation.
            self.acks_queue = Queue()
            self.delay_queue = PriorityQueue()

        except Exception as e:
            self.logger.error("Consumer encountered an error.", exc_info=True)
            # Avoid leaving any open file descriptors around when
            # an exception occurs.
            self.close()

        # The consumer must retry itself with exponential backoff
        # assuming it hasn't been shut down.
        if self.running:
            attempts, backoff_ms = compute_backoff(attempts, jitter=False, factor=100, max_backoff=60000)
            self.logger.debug("Waiting for %d milliseconds before restarting...", backoff_ms)
            self.close()
            time.sleep(backoff_ms / 1000)
            return self.run(attempts=attempts)

        self.broker.emit_before("consumer_thread_shutdown", self)
        self.logger.debug("Consumer thread stopped.")

    def handle_acks(self):
        """Perform any pending (n)acks.
        """
        for message in iter_queue(self.acks_queue):
            if message.failed:
                self.logger.debug("Rejecting message %r.", message.message_id)
                self.broker.emit_before("nack", message)
                self.consumer.nack(message)
                self.broker.emit_after("nack", message)

            else:
                self.logger.debug("Acknowledging message %r.", message.message_id)
                self.broker.emit_before("ack", message)
                self.consumer.ack(message)
                self.broker.emit_after("ack", message)

            self.acks_queue.task_done()

    def handle_delayed_messages(self):
        """Enqueue any delayed messages whose eta has passed.
        """
        for eta, message in iter_queue(self.delay_queue):
            if eta > current_millis():
                self.delay_queue.put((eta, message))
                self.delay_queue.task_done()
                break

            queue_name = q_name(message.queue_name)
            new_message = message.copy(queue_name=queue_name)
            del new_message.options["eta"]

            self.broker.enqueue(new_message)
            self.post_process_message(message)
            self.delay_queue.task_done()

    def handle_message(self, message):
        """Handle a message received off of the underlying consumer.
        If the message has an eta, delay it.  Otherwise, put it on the
        work queue.
        """
        try:
            if "eta" in message.options:
                self.logger.debug("Pushing message %r onto delay queue.", message.message_id)
                self.broker.emit_before("delay_message", message)
                self.delay_queue.put((message.options.get("eta", 0), message))

            else:
                actor = self.broker.get_actor(message.actor_name)
                self.logger.debug("Pushing message %r onto work queue.", message.message_id)
                self.work_queue.put((actor.priority, message))
        except ActorNotFound:
            self.logger.error(
                "Received message for undefined actor %r. Moving it to the DLQ.",
                message.actor_name, exc_info=True,
            )
            message.fail()
            self.post_process_message(message)

    def post_process_message(self, message):
        """Called by worker threads whenever they're done processing
        individual messages, signaling that each message is ready to
        be acked or rejected.
        """
        self.acks_queue.put(message)
        self.consumer.interrupt()

    def requeue_messages(self, messages):
        """Called on worker shutdown and whenever there is a
        connection error to move unacked messages back to their
        respective queues asap.
        """
        self.consumer.requeue(messages)

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
        try:
            if self.consumer:
                self.handle_acks()
                self.requeue_messages(m for _, m in iter_queue(self.delay_queue))
                self.consumer.close()
        except ConnectionError:
            pass


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
        self.paused = False
        self.paused_event = Event()
        self.broker = broker
        self.consumers = consumers
        self.work_queue = work_queue
        self.timeout = worker_timeout / 1000

    def run(self):
        self.logger.debug("Running worker thread...")
        self.running = True
        while self.running:
            if self.paused:
                self.logger.debug("Worker is paused. Sleeping for %.02f...", self.timeout)
                self.paused_event.set()
                time.sleep(self.timeout)
                continue

            try:
                _, message = self.work_queue.get(timeout=self.timeout)
                self.process_message(message)
            except Empty:
                continue

        self.broker.emit_before("worker_thread_shutdown", self)
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

        except SkipMessage as e:
            self.logger.warning("Message %s was skipped.", message)
            self.broker.emit_after("skip_message", message)

        except BaseException as e:
            self.logger.warning("Failed to process message %s with unhandled exception.", message, exc_info=True)
            self.broker.emit_after("process_message", message, exception=e)

        finally:
            # NOTE: There is no race here as any message that was
            # processed must have come off of a consumer.  Therefore,
            # there has to be a consumer for that message's queue so
            # this is safe.  Probably.
            self.consumers[message.queue_name].post_process_message(message)
            self.work_queue.task_done()

    def pause(self):
        """Pause this worker.
        """
        self.paused = True
        self.paused_event.clear()

    def resume(self):
        """Resume this worker.
        """
        self.paused = False
        self.paused_event.clear()

    def stop(self):
        """Initiate the WorkerThread shutdown process.

        Code calling this method should then join on the thread and
        wait for it to finish shutting down.
        """
        self.logger.debug("Stopping worker thread...")
        self.running = False
