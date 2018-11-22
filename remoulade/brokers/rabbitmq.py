# This file is a part of Remoulade.
#
# Copyright (C) 2017,2018 CLEARTYPE SRL <bogdan@cleartype.io>
#
# Remoulade is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# Remoulade is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import time
from functools import partial
from itertools import chain
from threading import local

import pika
from pika.exceptions import AMQPChannelError, AMQPConnectionError

from ..broker import Broker, Consumer, MessageProxy
from ..common import current_millis, dq_name, xq_name
from ..errors import ConnectionClosed, QueueJoinTimeout
from ..logging import get_logger
from ..message import Message

#: The maximum amount of time a message can be in the dead queue.
DEAD_MESSAGE_TTL = 86400000 * 7

#: The max number of times to attempt an enqueue operation in case of
#: a connection error.
MAX_ENQUEUE_ATTEMPTS = 6


class RabbitmqBroker(Broker):
    """A broker that can be used with RabbitMQ.

    Examples:

      If you want to specify connection parameters individually:

      >>> RabbitmqBroker(host="127.0.0.1", port=5672)

      Alternatively, if you want to use a connection URL:

      >>> RabbitmqBroker(url="amqp://guest:guest@127.0.0.1:5672")

    See also:
      ConnectionParameters_ for a list of all the available connection
      parameters.

    Parameters:
      confirm_delivery(bool): Wait for RabbitMQ to confirm that
        messages have been committed on every call to enqueue.
        Defaults to False.
      url(str): An optional connection URL.  If both a URL and
        connection parameters are provided, the URL is used.
      middleware(list[Middleware]): The set of middleware that apply
        to this broker.
      **parameters(dict): The (pika) connection parameters to use to
        determine which Rabbit server to connect to.

    .. _ConnectionParameters: https://pika.readthedocs.io/en/0.10.0/modules/parameters.html
    """

    def __init__(self, *, confirm_delivery=False, url=None, middleware=None, **parameters):
        super().__init__(middleware=middleware)

        if url:
            self.parameters = pika.URLParameters(url)
        else:
            self.parameters = pika.ConnectionParameters(**parameters)

        self.confirm_delivery = confirm_delivery
        self.connections = set()
        self.channels = set()
        self.queues = set()
        self.declared_queues = set()
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
        except (AttributeError, KeyError):
            pass

    @property
    def channel(self):
        """The :class:`pika.BlockingChannel` for the current thread.
        This property may change without notice.
        """
        channel = getattr(self.state, "channel", None)
        if channel is None:
            channel = self.state.channel = self.connection.channel()
            if self.confirm_delivery:
                channel.confirm_delivery()

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
        # The main thread may keep connections open for a long time
        # w/o publishing heartbeats, which means that they'll end up
        # being closed by the time the broker is closed.  When that
        # happens, pika logs a bunch of scary stuff so we want to
        # filter that out.
        logging_filter = _IgnoreScaryLogs()
        logging.getLogger("pika.adapters.base_connection").addFilter(logging_filter)
        logging.getLogger("pika.adapters.blocking_connection").addFilter(logging_filter)

        self.logger.debug("Closing channels and connections...")
        for channel_or_conn in chain(self.channels, self.connections):
            try:
                channel_or_conn.close()
            except pika.exceptions.AMQPError:
                pass

            except Exception:  # pragma: no cover
                self.logger.debug("Encountered an error while closing %r.", channel_or_conn, exc_info=True)
        self.channels = set()
        self.connections = set()
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
        try:
            self._declare_rabbitmq_queues()
        except (AMQPConnectionError, AMQPChannelError) as e:
            # Delete the channel and the connection so that the next
            # caller may initiate new ones of each.
            del self.channel
            del self.connection
            raise ConnectionClosed(e) from None
        return _RabbitmqConsumer(self.parameters, queue_name, prefetch, timeout)

    def _declare_rabbitmq_queues(self):
        """ Real Queue declaration to happen before enqueuing or consuming

        Raises:
          AMQPConnectionError or AMQPChannelError: If the underlying channel or connection has been closed.
        """
        for queue_name in self.queues:
            if queue_name not in self.declared_queues:
                self._declare_queue(queue_name)
                self._declare_dq_queue(queue_name)
                self._declare_xq_queue(queue_name)
                self.declared_queues.add(queue_name)

    def declare_queue(self, queue_name):
        """Declare a queue.  Has no effect if a queue with the given
        name already exists.

        Parameters:
          queue_name(str): The name of the new queue.

        Raises:
          ConnectionClosed: If the underlying channel or connection
            has been closed.
        """
        if queue_name not in self.queues:
            self.emit_before("declare_queue", queue_name)
            self.queues.add(queue_name)
            self.emit_after("declare_queue", queue_name)

            delayed_name = dq_name(queue_name)
            self.delay_queues.add(delayed_name)
            self.emit_after("declare_delay_queue", delayed_name)

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
            queue_name = dq_name(queue_name)
            message_eta = current_millis() + delay
            message = message.copy(
                queue_name=queue_name,
                options={
                    "eta": message_eta,
                },
            )

        attempts = 1
        while True:
            try:
                self._declare_rabbitmq_queues()
                self.logger.debug("Enqueueing message %r on queue %r.", message.message_id, queue_name)
                self.emit_before("enqueue", message, delay)
                self.channel.publish(
                    exchange="",
                    routing_key=queue_name,
                    body=message.encode(),
                    properties=properties,
                )
                self.emit_after("enqueue", message, delay)
                return message

            except (AMQPConnectionError, AMQPChannelError) as e:
                # Delete the channel and the connection so that the
                # next caller/attempt may initiate new ones of each.
                del self.channel
                del self.connection

                attempts += 1
                if attempts > MAX_ENQUEUE_ATTEMPTS:
                    raise ConnectionClosed(e) from None

                self.logger.debug(
                    "Retrying enqueue due to closed connection. [%d/%d]",
                    attempts, MAX_ENQUEUE_ATTEMPTS,
                )

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

    def flush(self, queue_name):
        """Drop all the messages from a queue.

        Parameters:
          queue_name(str): The queue to flush.
        """
        for name in (queue_name, dq_name(queue_name), xq_name(queue_name)):
            self.channel.queue_purge(name)

    def flush_all(self):
        """Drop all messages from all declared queues.
        """
        for queue_name in self.queues:
            self.flush(queue_name)

    def join(self, queue_name, min_successes=10, idle_time=100, *, timeout=None):
        """Wait for all the messages on the given queue to be
        processed.  This method is only meant to be used in tests to
        wait for all the messages in a queue to be processed.

        Warning:
          This method doesn't wait for unacked messages so it may not
          be completely reliable.  Use the stub broker in your unit
          tests and only use this for simple integration tests.

        Parameters:
          queue_name(str): The queue to wait on.
          min_successes(int): The minimum number of times all the
            polled queues should be empty.
          idle_time(int): The number of milliseconds to wait between
            counts.
          timeout(Optional[int]): The max amount of time, in
            milliseconds, to wait on this queue.
        """
        deadline = timeout and time.monotonic() + timeout / 1000
        successes = 0
        while successes < min_successes:
            if deadline and time.monotonic() >= deadline:
                raise QueueJoinTimeout(queue_name)

            total_messages = sum(self.get_queue_message_counts(queue_name)[:-1])
            if total_messages == 0:
                successes += 1
            else:
                successes = 0

            self.connection.sleep(idle_time / 1000)


class _IgnoreScaryLogs(logging.Filter):
    def filter(self, record):
        return "Broken pipe" not in record.getMessage()


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
        except (pika.exceptions.AMQPConnectionError,
                pika.exceptions.AMQPChannelError) as e:
            raise ConnectionClosed(e) from None

    def ack(self, message):
        try:
            self.known_tags.remove(message._tag)
            self.connection.add_callback_threadsafe(
                partial(self.channel.basic_ack, message._tag),
            )
        except (pika.exceptions.AMQPConnectionError,
                pika.exceptions.AMQPChannelError) as e:
            raise ConnectionClosed(e) from None
        except KeyError:
            self.logger.warning("Failed to ack message: not in known tags.")
        except Exception:  # pragma: no cover
            self.logger.warning("Failed to ack message.", exc_info=True)

    def nack(self, message):
        try:
            self.known_tags.remove(message._tag)
            self.connection.add_callback_threadsafe(
                partial(self.channel.basic_nack, message._tag, requeue=False),
            )
        except (pika.exceptions.AMQPConnectionError,
                pika.exceptions.AMQPChannelError) as e:
            raise ConnectionClosed(e) from None
        except KeyError:
            self.logger.warning("Failed to nack message: not in known tags.")
        except Exception:  # pragma: no cover
            self.logger.warning("Failed to nack message.", exc_info=True)

    def requeue(self, messages):
        """RabbitMQ automatically re-enqueues unacked messages when
        consumers disconnect so this is a no-op.
        """

    def __next__(self):
        try:
            method, properties, body = next(self.iterator)
            if method is None:
                return None

            message = Message.decode(body)
            self.known_tags.add(method.delivery_tag)
            return _RabbitmqMessage(method.delivery_tag, message)
        except (AssertionError,
                pika.exceptions.AMQPConnectionError,
                pika.exceptions.AMQPChannelError) as e:
            raise ConnectionClosed(e) from None

    def close(self):
        try:
            self.channel.close()
            self.connection.close()
        except (AssertionError,
                pika.exceptions.AMQPConnectionError,
                pika.exceptions.AMQPChannelError) as e:
            raise ConnectionClosed(e) from None


class _RabbitmqMessage(MessageProxy):
    def __init__(self, tag, message):
        super().__init__(message)

        self._tag = tag
