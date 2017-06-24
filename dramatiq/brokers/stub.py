from queue import Queue, Empty

from ..broker import Broker, Consumer, MessageProxy
from ..common import current_millis, dq_name, xq_name
from ..errors import QueueNotFound
from ..message import Message


class StubBroker(Broker):
    """A broker that can be used within unit tests.
    """

    def __init__(self, middleware=None):
        super().__init__(middleware)

        self.dead_letters = []

    def consume(self, queue_name, prefetch=1, timeout=100):
        try:
            return _StubConsumer(
                self.queues[queue_name],
                self.dead_letters,
                timeout
            )
        except KeyError:
            raise QueueNotFound(queue_name)

    def declare_queue(self, queue_name):
        self.emit_before("declare_queue", queue_name)
        self.queues[queue_name] = Queue()
        self.queues[xq_name(queue_name)] = Queue()
        self.emit_after("declare_queue", queue_name)

        delayed_name = dq_name(queue_name)
        self.queues[delayed_name] = Queue()
        self.delay_queues.add(delayed_name)
        self.emit_after("declare_delay_queue", delayed_name)

    def enqueue(self, message, *, delay=None):
        queue_name = message.queue_name
        if delay is not None:
            queue_name = dq_name(queue_name)
            message = message._replace(queue_name=queue_name)
            message.options["eta"] = current_millis() + delay

        self.emit_before("enqueue", message, delay)
        self.queues[queue_name].put(message.encode())
        self.emit_after("enqueue", message, delay)

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
            for queue_name in (queue_name, dq_name(queue_name)):
                self.queues[queue_name].join()
        except KeyError:
            raise QueueNotFound(queue_name)


class _StubConsumer(Consumer):
    def __init__(self, queue, dead_letters, timeout):
        self.queue = queue
        self.dead_letters = dead_letters
        self.timeout = timeout

    def ack(self, message):
        self.queue.task_done()

    def nack(self, message):
        self.queue.task_done()
        self.dead_letters.append(message)

    def __next__(self):
        try:
            data = self.queue.get(timeout=self.timeout / 1000)
            message = Message.decode(data)
            return MessageProxy(message)
        except Empty:
            return None
