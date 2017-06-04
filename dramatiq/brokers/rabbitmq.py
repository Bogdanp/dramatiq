import pika
import time

from threading import local

from ..broker import Broker, Consumer, MessageProxy
from ..errors import ConnectionClosed
from ..message import Message


#: Default properties for enqueued messages.
_properties = pika.BasicProperties(delivery_mode=2)


def _dq_name(queue_name):
    """Returns the delayed queue name for a given queue.
    """
    return f"{queue_name}.DQ"


def _dq_arguments(queue_name):
    """Returns the delayed queue arguments for a given queue.
    """
    return {
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": queue_name,
    }


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
                connection.close()
            except pika.exceptions.ConnectionClosed as e:
                pass

        self.logger.debug("Connections closed.")

    def consume(self, queue_name, timeout=5):
        return _RabbitmqConsumer(self.parameters, queue_name, timeout)

    def declare_queue(self, queue_name):
        try:
            if queue_name not in self.queues:
                self._emit_before("declare_queue", queue_name)
                self.channel.queue_declare(queue=queue_name, durable=True)
                self.channel.queue_declare(queue=_dq_name(queue_name), durable=True, arguments=_dq_arguments(queue_name))  # noqa
                self.queues.add(queue_name)
                self._emit_after("declare_queue", queue_name)
        except pika.exceptions.ConnectionClosed as e:
            raise ConnectionClosed(e)

    def enqueue(self, message, *, delay=None):
        self.logger.debug("Enqueueing message %r on queue %r.", message.message_id, message.queue_name)
        self._emit_before("enqueue", message, delay)

        if delay is not None:
            self._enqueue(_dq_name(message.queue_name), message, properties=pika.BasicProperties(
                delivery_mode=2,
                expiration=str(delay),
            ))
        else:
            self._enqueue(message.queue_name, message)

        self._emit_after("enqueue", message, delay)

    def _enqueue(self, queue_name, message, *, properties=_properties):
        self.channel.publish(
            exchange="",
            routing_key=queue_name,
            body=message.encode(),
            properties=properties,
        )

    def get_declared_queues(self):
        return self.queues

    def join(self, queue_name, timeout=1000):
        """Wait for all the messages on the given queue to be
        processed.  This method is only meant to be used in tests to
        wait for all the messages in a queue to be processed.

        Note:
          This method doesn't wait for unacked messages so it may not
          be completely reliable.  Use the stub broker in your unit
          tests and only use this for simple integration tests.

        Parameters:
          queue_name(str)
          timeout(int)
        """
        while True:
            response = self.channel.queue_declare(queue=queue_name, durable=True)
            total_messages = response.method.message_count

            response = self.channel.queue_declare(queue=_dq_name(queue_name), durable=True, arguments=_dq_arguments(queue_name))  # noqa
            total_messages += response.method.message_count

            if total_messages == 0:
                return

            time.sleep(timeout / 1000)


class _RabbitmqConsumer(Consumer):
    def __init__(self, parameters, queue_name, timeout):
        try:
            self.connection = pika.BlockingConnection(parameters=parameters)
            self.channel = self.connection.channel()
            self.channel.basic_qos(prefetch_count=1)
            self.iterator = self.channel.consume(queue_name, inactivity_timeout=timeout)
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
        self.channel.cancel()
        self.connection.close()


class _RabbitmqMessage(MessageProxy):
    def __init__(self, channel, message, tag):
        self._channel = channel
        self._message = message
        self._tag = tag

    def acknowledge(self):
        self._channel.basic_ack(self._tag)
