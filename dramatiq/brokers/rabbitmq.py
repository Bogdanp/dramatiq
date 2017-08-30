import pika

from itertools import chain
from threading import local

from ..broker import Broker, Consumer, MessageProxy
from ..common import current_millis, dq_name, xq_name
from ..errors import ConnectionClosed
from ..logging import get_logger
from ..message import Message

#: The maximum amount of time a message can be in the dead queue.
DEAD_MESSAGE_TTL = 86400 * 7 * 1000

#: The max amount of time messages can be delayed by in ms.
MAX_MESSAGE_DELAY = 86400000 * 7


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
        self.channels = set()
        self.queues = set()
        self.state = local()

    @property
    def connection(self):
        """The :class:`pika.BlockingConnection` for the current
        thread.  This property may change without notice.
        """
        connection = getattr(self.state, "connection", None)
        if connection is None:
            connection = self.state.connection = pika.BlockingConnection(
                parameters=self.parameters)
            self.connections.add(connection)
        return connection

    @connection.deleter
    def connection(self):
        try:
            connection = self.state.connection
            del self.state.connection
            self.connections.remove(connection)
        except AttributeError:
            pass

    @property
    def channel(self):
        """The :class:`pika.BlockingChannel` for the current thread.
        This property may change without notice.
        """
        channel = getattr(self.state, "channel", None)
        if channel is None:
            channel = self.state.channel = self.connection.channel()
            self.channels.add(channel)
        return channel

    @channel.deleter
    def channel(self):
        try:
            channel = self.state.channel
            del self.state.channel
            self.channels.remove(channel)
        except AttributeError:
            pass

    def close(self):
        """Close all open RabbitMQ connections.
        """
        self.logger.debug("Closing channels and connections...")
        for channel_or_conn in chain(self.channels, self.connections):
            try:
                channel_or_conn.close()

            except (pika.exceptions.ChannelClosed,
                    pika.exceptions.ConnectionClosed):
                pass

            except Exception:  # pragma: no cover
                self.logger.debug("Encountered an error while closing %r.", channel_or_conn, exc_info=True)
        self.logger.debug("Channels and connections closed.")

    def consume(self, queue_name, prefetch=1, timeout=5000):
        """Create a new consumer for a queue.

        Parameters:
          queue_name(str): The queue to consume.
          prefetch(int): The number of messages to prefetch.
          timeout(int): The idle timeout in milliseconds.

        Returns:
          Consumer: A consumer that retrieves messages from RabbitMQ.
        """
        return _RabbitmqConsumer(self.parameters, queue_name, prefetch, timeout)

    def declare_queue(self, queue_name):
        """Declare a queue.  Has no effect if a queue with the given
        name already exists.

        Parameters:
          queue_name(str): The name of the new queue.

        Raises:
          ConnectionClosed: If the underlying channel or connection
            has been closed.
        """
        try:
            if queue_name not in self.queues:
                self.emit_before("declare_queue", queue_name)
                self._declare_queue(queue_name)
                self.queues.add(queue_name)
                self.emit_after("declare_queue", queue_name)

                delayed_name = dq_name(queue_name)
                self._declare_dq_queue(queue_name)
                self.delay_queues.add(delayed_name)
                self.emit_after("declare_delay_queue", delayed_name)

                self._declare_xq_queue(queue_name)
        except (pika.exceptions.ChannelClosed,
                pika.exceptions.ConnectionClosed) as e:  # pragma: no cover
            # Delete the channel and the connection so that the next
            # caller may initiate new ones of each.
            del self.consumer
            del self.connection
            raise ConnectionClosed(e) from None

    def _declare_queue(self, queue_name):
        return self.channel.queue_declare(queue=queue_name, durable=True, arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": xq_name(queue_name),
        })

    def _declare_dq_queue(self, queue_name):
        return self.channel.queue_declare(queue=dq_name(queue_name), durable=True, arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": xq_name(queue_name),
        })

    def _declare_xq_queue(self, queue_name):
        return self.channel.queue_declare(queue=xq_name(queue_name), durable=True, arguments={
            # This HAS to be a static value since messages are expired
            # in order inside of RabbitMQ (head-first).
            "x-message-ttl": DEAD_MESSAGE_TTL,
        })

    def enqueue(self, message, *, delay=None):
        """Enqueue a message.

        Parameters:
          message(Message): The message to enqueue.
          delay(int): The minimum amount of time, in milliseconds, to
            delay the message by.

        Raises:
          ConnectionClosed: If the underlying channel or connection
            has been closed.
        """
        queue_name = message.queue_name
        properties = pika.BasicProperties(delivery_mode=2)
        if delay is not None:
            if delay > MAX_MESSAGE_DELAY:
                raise ValueError(
                    "Messages cannot be delayed for longer than 7 days. "
                    "Your message queue is not a Database."
                )

            queue_name = dq_name(queue_name)
            message = message._replace(queue_name=queue_name)
            message.options["eta"] = current_millis() + delay

        try:
            self.logger.debug("Enqueueing message %r on queue %r.", message.message_id, queue_name)
            self.emit_before("enqueue", message, delay)
            self.channel.publish(
                exchange="",
                routing_key=queue_name,
                body=message.encode(),
                properties=properties,
            )
            self.emit_after("enqueue", message, delay)
        except (pika.exceptions.ChannelClosed,
                pika.exceptions.ConnectionClosed) as e:
            # Delete the channel and the connection so that the next
            # caller may initiate new ones of each.
            del self.channel
            del self.connection
            raise ConnectionClosed(e) from None

    def get_declared_queues(self):
        """Get all declared queues.

        Returns:
          set[str]: The names of all the queues declared so far on
          this Broker.
        """
        return self.queues.copy()

    def get_queue_message_counts(self, queue_name):
        """Get the number of messages in a queue.  This method is only
        meant to be used in unit and integration tests.

        Parameters:
          queue_name(str): The queue whose message counts to get.

        Returns:
          tuple: A triple representing the number of messages in the
          queue, its delayed queue and its dead letter queue.
        """
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
        successes = 0
        while successes < 3:
            total_messages = sum(self.get_queue_message_counts(queue_name)[:-1])
            if total_messages == 0:
                successes += 1

            self.connection.sleep(1)


class _RabbitmqConsumer(Consumer):
    def __init__(self, parameters, queue_name, prefetch, timeout):
        try:
            self.logger = get_logger(__name__, type(self))
            self.connection = pika.BlockingConnection(parameters=parameters)
            self.channel = self.connection.channel()
            self.channel.basic_qos(prefetch_count=prefetch)
            self.iterator = self.channel.consume(queue_name, inactivity_timeout=timeout / 1000)

            # We need to keep track of known delivery tags so that
            # when connection errors occur and the consumer is reset,
            # we don't attempt to send invalid tags to Rabbit since
            # pika doesn't handle this very well.
            self.known_tags = set()
        except pika.exceptions.ConnectionClosed as e:
            raise ConnectionClosed(e) from None

    def ack(self, message):
        try:
            self.known_tags.remove(message._tag)
            self.channel.basic_ack(message._tag)
        except pika.exceptions.ChannelClosed as e:
            raise ConnectionClosed(e) from None
        except KeyError:
            self.logger.warning("Failed to ack message: not in known tags.")
        except Exception:
            self.logger.warning("Failed to ack message.", exc_info=True)

    def nack(self, message):
        try:
            self.known_tags.remove(message._tag)
            self.channel.basic_nack(message._tag, requeue=False)
        except pika.exceptions.ChannelClosed as e:
            raise ConnectionClosed(e) from None
        except KeyError:
            self.logger.warning("Failed to nack message: not in known tags.")
        except Exception:
            self.logger.warning("Failed to nack message.", exc_info=True)

    def requeue(self, messages):
        """RabbitMQ automatically re-enqueues unacked messages when
        consumers disconnect so this is a no-op.
        """

    def __next__(self):
        try:
            frame = next(self.iterator)
            if frame is None:
                return None

            method, properties, body = frame
            message = Message.decode(body)
            self.known_tags.add(method.delivery_tag)
            return _RabbitmqMessage(method.delivery_tag, message)
        except (AssertionError,  # sometimes raised by pika
                pika.exceptions.ChannelClosed,
                pika.exceptions.ConnectionClosed) as e:
            raise ConnectionClosed(e) from None

    def close(self):
        try:
            if self.channel.is_open:
                self.channel.cancel()

            self.channel.close()
            self.connection.close()
        except (AssertionError,  # sometimes raised by pika
                pika.exceptions.ChannelClosed,
                pika.exceptions.ConnectionClosed) as e:
            raise ConnectionClosed(e) from None


class _RabbitmqMessage(MessageProxy):
    def __init__(self, tag, message):
        super().__init__(message)

        self._tag = tag
