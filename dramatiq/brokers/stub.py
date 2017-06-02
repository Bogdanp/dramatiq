from queue import Queue, Empty

from ..broker import Broker, Consumer
from ..errors import QueueNotFound
from ..message import Message


class StubBroker(Broker):
    """A broker that can be used within unit tests.
    """

    def consume(self, queue_name, timeout=0.1):
        try:
            queue = self.queues[queue_name]
            return _StubConsumer(queue, timeout)
        except KeyError:
            raise QueueNotFound(queue_name)

    def declare_queue(self, queue_name):
        if queue_name not in self.queues:
            self._emit_before("declare_queue", queue_name)
            self.queues[queue_name] = Queue()
            self._emit_after("declare_queue", queue_name)

    def enqueue(self, message):
        self._emit_before("enqueue", message)
        self.queues[message.queue_name].put(message.encode())
        self._emit_after("enqueue", message)

    def join(self, queue_name):
        """Wait for all the messages on the given queue to be processed.

        Raises:
          QueueNotFound: If the given queue was never declared.

        Parameters:
          queue_name(str)
        """
        try:
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
            data = self.queue.get(timeout=self.timeout)
            message = Message.decode(data)
            return _StubMessage(message, self.queue)
        except Empty:
            return None


class _StubMessage:
    def __init__(self, message, queue):
        self._message = message
        self._queue = queue

    def acknowledge(self):
        self._queue.task_done()

    def __getattr__(self, name):
        return getattr(self._message, name)

    def __str__(self):
        return str(self._message)
