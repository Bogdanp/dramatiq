from collections import defaultdict
from queue import Queue, Empty
from threading import Timer

from ..broker import Broker, Consumer, MessageProxy
from ..errors import QueueNotFound
from ..message import Message


class StubBroker(Broker):
    """A broker that can be used within unit tests.
    """

    def __init__(self, middleware=None):
        super().__init__(middleware)

        self.timers_by_queue = defaultdict(list)

    def consume(self, queue_name, prefetch=1, timeout=100):
        try:
            queue = self.queues[queue_name]
            return _StubConsumer(queue, timeout)
        except KeyError:
            raise QueueNotFound(queue_name)

    def declare_queue(self, queue_name):
        if queue_name not in self.queues:
            self.emit_before("declare_queue", queue_name)
            self.queues[queue_name] = Queue()
            self.emit_after("declare_queue", queue_name)

    def enqueue(self, message, *, delay=None):
        self.emit_before("enqueue", message, delay)

        if delay is not None:
            timer = Timer(delay / 1000, self._enqueue, args=(message,))
            timer.start()
            self.timers_by_queue[message.queue_name].append(timer)
        else:
            self._enqueue(message)

        self.emit_after("enqueue", message, delay)

    def _enqueue(self, message):
        self.queues[message.queue_name].put(message.encode())

    def join(self, queue_name):
        """Wait for all the messages on the given queue to be
        processed.  This method is only meant to be used in tests
        to wait for all the messages in a queue to be processed.

        Raises:
          QueueNotFound: If the given queue was never declared.

        Parameters:
          queue_name(str): The queue to wait on.
        """
        try:
            self.queues[queue_name].join()

            timers = self.timers_by_queue[queue_name]
            while timers:
                timer = timers.pop(0)
                timer.join()
                self.queues[queue_name].join()
        except KeyError:
            raise QueueNotFound(queue_name)


class _StubConsumer(Consumer):
    def __init__(self, queue, timeout):
        self.queue = queue
        self.timeout = timeout

    def __iter__(self):
        return self

    def __next__(self):
        try:
            data = self.queue.get(timeout=self.timeout / 1000)
            message = Message.decode(data)
            return _StubMessage(message, self.queue)
        except Empty:
            return None


class _StubMessage(MessageProxy):
    def __init__(self, message, queue):
        super().__init__(message)
        self._queue = queue

    def acknowledge(self):
        self._queue.task_done()

    def reject(self):
        self._queue.task_done()
