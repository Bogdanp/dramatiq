import pika

from threading import local

from ..broker import Broker, Consumer
from ..errors import ConnectionClosed
from ..message import Message


_properties = pika.BasicProperties(delivery_mode=2)


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
        self.logger.info("Closing connections...")
        for connection in self.connections:
            try:
                connection.close()
            except pika.exceptions.ConnectionClosed as e:
                pass

        self.logger.info("Connections closed.")

    def consume(self, queue_name, timeout=5):
        return _RabbitmqConsumer(self.parameters, queue_name, timeout)

    def declare_queue(self, queue_name):
        try:
            if queue_name not in self.queues:
                self._emit_before("declare_queue", queue_name)
                self.channel.queue_declare(queue=queue_name, durable=True)
                self.queues.add(queue_name)
                self._emit_after("declare_queue", queue_name)
        except pika.exceptions.ConnectionClosed as e:
            raise ConnectionClosed(e)

    def enqueue(self, message):
        self.logger.info("Enqueueing message %r on queue %r.", message.message_id, message.queue_name)
        self._emit_before("enqueue", message)
        self.channel.publish(
            exchange="",
            routing_key=message.queue_name,
            body=message.encode(),
            properties=_properties,
        )
        self._emit_after("enqueue", message)

    def get_declared_queues(self):
        return self.queues


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


class _RabbitmqMessage:
    def __init__(self, channel, message, tag):
        self._channel = channel
        self._message = message
        self._tag = tag

    def acknowledge(self):
        self._channel.basic_ack(self._tag)

    def __getattr__(self, name):
        return getattr(self._message, name)

    def __str__(self):
        return str(self._message)
