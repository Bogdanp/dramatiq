import pika

from ..broker import Broker, Consumer, QueueNotFound
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

        self.connection = pika.BlockingConnection(parameters=parameters)
        self.channel = self.connection.channel()

    def acknowledge(self, queue_name, ack_id):
        try:
            channel = self.queues[queue_name]
            channel.basic_ack(delivery_tag=ack_id)
        except KeyError:
            raise QueueNotFound(queue_name)

    def declare_queue(self, queue_name):
        if queue_name not in self.queues:
            self._emit_before("declare_queue", queue_name)
            channel = self.connection.channel()
            channel.queue_declare(queue=queue_name, durable=True)
            self.queues[queue_name] = channel
            self._emit_after("declare_queue", queue_name)

    def enqueue(self, message):
        self._emit_before("enqueue", message)
        self.channel.publish(
            exchange="",
            routing_key=message.queue_name,
            body=message.encode(),
            properties=_properties,
        )
        self._emit_after("enqueue", message)

    def get_consumer(self, queue_name, on_message):
        try:
            channel = self.queues[queue_name]

            def relay(ch, method, properties, body):
                on_message(Message.decode(body), method.delivery_tag)

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(relay, queue_name)
            return _RabbitmqConsumer(channel)
        except KeyError:
            raise QueueNotFound(queue_name)


class _RabbitmqConsumer(Consumer):
    def __init__(self, channel):
        self.channel = channel

    def start(self):
        self.channel.start_consuming()

    def stop(self):
        self.channel.stop_consuming()
