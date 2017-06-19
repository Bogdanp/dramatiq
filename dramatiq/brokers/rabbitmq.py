import pika
import time

from threading import local

from ..broker import Broker, Consumer, MessageProxy
from ..errors import ConnectionClosed
from ..message import Message

#: The maximum amount of time a message can be in the dead queue.
_dead_message_ttl = 86400 * 7 * 1000


def _dq_name(queue_name):
    """Returns the delayed queue name for a given queue.
    """
    return f"{queue_name}.DQ"


def _xq_name(queue_name):
    """Returns the dead letter queue name for a given queue.
    """
    return f"{queue_name}.XQ"


class RabbitmqBroker(Broker):
    """A broker that can be used with RabbitMQ.

    Parameters:
      parameters(pika.ConnectionParameters): The connection parameters
        to use to determine which Rabbit server to connect to.
      middleware(list[Middleware]): The set of middleware that apply
        to this broker.
    """

    def __init__(self, parameters=None, middleware=None):
        super().__init__(middleware=middleware)

        self.parameters = parameters
        self.connections = set()
        self.queues = set()
        self.state = local()

    @property
    def connection(self):
        connection = getattr(self.state, "connection", None)
        if connection is None:
            connection = self.state.connection = pika.BlockingConnection(
                parameters=self.parameters)
            self.connections.add(connection)
        return connection

    @property
    def channel(self):
        channel = getattr(self.state, "channel", None)
        if channel is None:
            channel = self.state.channel = self.connection.channel()
        return channel

    def close(self):
        self.logger.debug("Closing connections...")
        for connection in self.connections:
            try:
                if connection.is_open:
                    connection.close()
            except pika.exceptions.ConnectionClosed:
                self.logger.debug("Encountered an error while closing connection.", exc_info=True)

        self.logger.debug("Connections closed.")

    def consume(self, queue_name, prefetch=1, timeout=5000):
        return _RabbitmqConsumer(self.parameters, queue_name, prefetch, timeout)

    def declare_queue(self, queue_name):
        try:
            if queue_name not in self.queues:
                self.emit_before("declare_queue", queue_name)
                self._declare_queue(queue_name)
                self._declare_dq_queue(queue_name)
                self._declare_xq_queue(queue_name)
                self.queues.add(queue_name)
                self.emit_after("declare_queue", queue_name)
        except pika.exceptions.ConnectionClosed as e:
            raise ConnectionClosed(e)

    def _declare_queue(self, queue_name):
        return self.channel.queue_declare(queue=queue_name, durable=True, arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": _xq_name(queue_name),
        })

    def _declare_dq_queue(self, queue_name):
        return self.channel.queue_declare(queue=_dq_name(queue_name), durable=True, arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": queue_name,
        })

    def _declare_xq_queue(self, queue_name):
        return self.channel.queue_declare(queue=_xq_name(queue_name), durable=True, arguments={
            "x-message-ttl": _dead_message_ttl,
        })

    def enqueue(self, message, *, delay=None):
        self.logger.debug("Enqueueing message %r on queue %r.", message.message_id, message.queue_name)
        self.emit_before("enqueue", message, delay)

        queue_name = message.queue_name
        properties = pika.BasicProperties(delivery_mode=2)
        if delay is not None:
            queue_name = _dq_name(queue_name)
            properties.expiration = str(delay)

        self.channel.publish(
            exchange="",
            routing_key=queue_name,
            body=message.encode(),
            properties=properties,
        )
        self.emit_after("enqueue", message, delay)

    def get_declared_queues(self):
        return self.queues.copy()

    def get_queue_message_counts(self, queue_name):
        queue_response = self._declare_queue(queue_name)
        dq_queue_response = self._declare_dq_queue(queue_name)
        xq_queue_response = self._declare_xq_queue(queue_name)
        return (
            queue_response.method.message_count,
            dq_queue_response.method.message_count,
            xq_queue_response.method.message_count,
        )

    def join(self, queue_name):
        """Wait for all the messages on the given queue to be
        processed.  This method is only meant to be used in tests to
        wait for all the messages in a queue to be processed.

        Note:
          This method doesn't wait for unacked messages so it may not
          be completely reliable.  Use the stub broker in your unit
          tests and only use this for simple integration tests.

        Parameters:
          queue_name(str): The queue to wait on.
        """
        while True:
            total_messages = sum(self.get_queue_message_counts(queue_name)[:-1])
            if total_messages == 0:
                return

            time.sleep(1)


class _RabbitmqConsumer(Consumer):
    def __init__(self, parameters, queue_name, prefetch, timeout):
        try:
            self.connection = pika.BlockingConnection(parameters=parameters)
            self.channel = self.connection.channel()
            self.channel.basic_qos(prefetch_count=prefetch)
            self.iterator = self.channel.consume(queue_name, inactivity_timeout=timeout / 1000)
        except pika.exceptions.ConnectionClosed as e:
            raise ConnectionClosed(e)

    def __iter__(self):
        return self

    def __next__(self):
        try:
            frame = next(self.iterator)
            if frame is None:
                return None

            method, properties, body = frame
            message = Message.decode(body)
            return _RabbitmqMessage(self.channel, message, method.delivery_tag)
        except pika.exceptions.ConnectionClosed as e:
            raise ConnectionClosed(e)

    def close(self):
        if self.connection.is_open:
            self.channel.cancel()
            self.connection.close()


class _RabbitmqMessage(MessageProxy):
    def __init__(self, channel, message, tag):
        super().__init__(message)
        self._channel = channel
        self._tag = tag

    def acknowledge(self):
        self._channel.basic_ack(self._tag)

    def reject(self):
        self._channel.basic_nack(self._tag, requeue=False)
