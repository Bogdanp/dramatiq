from itertools import chain
from queue import Queue, Empty

from ..broker import Broker, Consumer, MessageProxy
from ..common import current_millis, dq_name, iter_queue
from ..errors import QueueNotFound
from ..message import Message


class StubBroker(Broker):
    """A broker that can be used within unit tests.

    Attributes:
      dead_letters(list[Message]): Contains the dead-lettered messages
        for all defined queues.
    """

    def __init__(self, middleware=None):
        super().__init__(middleware)

        self.dead_letters = []

    def consume(self, queue_name, prefetch=1, timeout=100):
        """Create a new consumer for a queue.

        Parameters:
          queue_name(str): The queue to consume.
          prefetch(int): The number of messages to prefetch.
          timeout(int): The idle timeout in milliseconds.

        Raises:
          QueueNotFound: If the queue hasn't been declared.

        Returns:
          Consumer: A consumer that retrieves messages from Redis.
        """
        try:
            return _StubConsumer(self.queues[queue_name], self.dead_letters, timeout)
        except KeyError:
            raise QueueNotFound(queue_name)

    def declare_queue(self, queue_name):
        """Declare a queue.  Has no effect if a queue with the given
        name has already been declared.

        Parameters:
          queue_name(str): The name of the new queue.
        """
        if queue_name not in self.queues:
            self.emit_before("declare_queue", queue_name)
            self.queues[queue_name] = Queue()
            self.emit_after("declare_queue", queue_name)

            delayed_name = dq_name(queue_name)
            self.queues[delayed_name] = Queue()
            self.delay_queues.add(delayed_name)
            self.emit_after("declare_delay_queue", delayed_name)

    def enqueue(self, message, *, delay=None):
        """Enqueue a message.

        Parameters:
          message(Message): The message to enqueue.
          delay(int): The minimum amount of time, in milliseconds, to
            delay the message by.

        Raises:
          QueueNotFound: If the queue the message is being enqueued on
            doesn't exist.
        """
        queue_name = message.queue_name
        if delay is not None:
            queue_name = dq_name(queue_name)
            message_eta = current_millis() + delay
            message = message.copy(
                queue_name=queue_name,
                options={
                    "eta": message_eta,
                },
            )

        if queue_name not in self.queues:
            raise QueueNotFound(queue_name)

        self.emit_before("enqueue", message, delay)
        self.queues[queue_name].put(message.encode())
        self.emit_after("enqueue", message, delay)
        return message

    def flush(self, queue_name):
        """Drop all the messages from a queue.

        Parameters:
          queue_name(str): The queue to flush.
        """
        for _ in iter_queue(self.queues[queue_name]):
            pass

    def flush_all(self):
        """Drop all messages from all declared queues.
        """
        for queue_name in chain(self.queues, self.delay_queues):
            self.flush(queue_name)

    def join(self, queue_name):
        """Wait for all the messages on the given queue to be
        processed.  This method is only meant to be used in tests
        to wait for all the messages in a queue to be processed.

        Parameters:
          queue_name(str): The queue to wait on.

        Raises:
          QueueNotFound: If the given queue was never declared.
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

    def requeue(self, messages):
        pass

    def __next__(self):
        try:
            data = self.queue.get(timeout=self.timeout / 1000)
            message = Message.decode(data)
            return MessageProxy(message)
        except Empty:
            return None
