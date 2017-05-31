import uuid

from queue import Queue, Empty

from ..broker import Broker, Consumer, QueueNotFound
from ..message import Message


class StubBroker(Broker):
    """A broker that can be used within unit tests.
    """

    def acknowledge(self, queue_name, ack_id):
        try:
            self._emit_before("acknowledge", queue_name, ack_id)
            queue = self.queues[queue_name]
            queue.task_done()
            self._emit_after("acknowledge", queue_name, ack_id)
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

    def get_consumer(self, queue_name, on_message):
        try:
            queue = self.queues[queue_name]
            return _StubConsumer(queue, on_message)
        except KeyError:
            raise QueueNotFound(queue_name)

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
    def __init__(self, queue, on_message):
        self.running = False
        self.queue = queue
        self.on_message = on_message

    def start(self):
        self.running = True
        while self.running:
            try:
                data = self.queue.get(timeout=0.1)
                message = Message.decode(data)
                self.on_message(message, str(uuid.uuid4()))
            except Empty:
                pass

    def stop(self):
        self.running = False
