# This file is a part of Dramatiq.
#
# Copyright (C) 2017,2018 CLEARTYPE SRL <bogdan@cleartype.io>
#
# Dramatiq is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# Dramatiq is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import os
import time
import warnings
from functools import partial
from itertools import chain
from threading import Event, local

import pika

from ..broker import Broker, Consumer, MessageProxy
from ..common import current_millis, dq_name, xq_name
from ..errors import ConnectionClosed, DecodeError, QueueJoinTimeout
from ..logging import get_logger
from ..message import Message, get_encoder

#: The maximum amount of time a message can be in the dead queue.
DEAD_MESSAGE_TTL = int(os.getenv("dramatiq_dead_message_ttl", 86400000 * 7))

#: The max number of times to attempt an enqueue operation in case of
#: a connection error.
MAX_ENQUEUE_ATTEMPTS = 6
MAX_DECLARE_ATTEMPTS = 2


class RabbitmqBroker(Broker):
    """A broker that can be used with RabbitMQ.

    Examples:

      If you want to specify connection parameters individually:

      >>> RabbitmqBroker(host="127.0.0.1", port=5672)

      Alternatively, if you want to use a connection URL:

      >>> RabbitmqBroker(url="amqp://guest:guest@127.0.0.1:5672")

      To support message priorities, provide a ``max_priority``...

      >>> broker = RabbitmqBroker(url="...", max_priority=255)

      ... then enqueue messages with the ``broker_priority`` option:

      >>> broker.enqueue(an_actor.message_with_options(
      ...    broker_priority=255,
      ... ))

    See also:
      ConnectionParameters_ for a list of all the available connection
      parameters.

    Parameters:
      confirm_delivery(bool): Wait for RabbitMQ to confirm that
        messages have been committed on every call to enqueue.
        Defaults to False.
      url(str|list[str]): An optional connection URL.  If both a URL
        and connection parameters are provided, the URL is used.
      middleware(list[Middleware]): The set of middleware that apply
        to this broker.
      max_priority(int): Configure queues with ``x-max-priority`` to
        support queue-global priority queueing.
      parameters(list[dict]): A sequence of (pika) connection parameters
        to determine which Rabbit server(s) to connect to.
      **kwargs: The (pika) connection parameters to use to
        determine which Rabbit server to connect to.

    .. _ConnectionParameters: https://pika.readthedocs.io/en/0.12.0/modules/parameters.html
    """

    def __init__(self, *, confirm_delivery=False, url=None, middleware=None, max_priority=None, parameters=None, **kwargs):
        super().__init__(middleware=middleware)

        if max_priority is not None and not (0 < max_priority <= 255):
            raise ValueError("max_priority must be a value between 0 and 255")

        if url is not None:
            if parameters is not None or kwargs:
                raise RuntimeError("the 'url' argument cannot be used in conjunction with pika parameters")

            if isinstance(url, str) and ";" in url:
                self.parameters = [pika.URLParameters(u) for u in url.split(";")]

            elif isinstance(url, list):
                self.parameters = [pika.URLParameters(u) for u in url]

            else:
                self.parameters = pika.URLParameters(url)

        elif parameters is not None:
            if kwargs:
                raise RuntimeError("the 'parameters' argument cannot be used in conjunction with other pika parameters")

            self.parameters = [pika.ConnectionParameters(**p) for p in parameters]

        else:
            self.parameters = pika.ConnectionParameters(**kwargs)

        self.confirm_delivery = confirm_delivery
        self.max_priority = max_priority
        self.connections = set()
        self.channels = set()
        self.queues = set()
        self.queues_pending = set()
        self.state = local()

    @property
    def consumer_class(self):
        return _RabbitmqConsumer

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
        del self.channel
        try:
            connection = self.state.connection
        except AttributeError:
            return

        del self.state.connection
        self.connections.remove(connection)
        if connection.is_open:
            try:
                connection.close()
            except Exception:
                self.logger.exception("Encountered exception while closing Connection.")

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
        except AttributeError:
            return

        del self.state.channel
        self.channels.remove(channel)
        if channel.is_open:
            try:
                channel.close()
            except Exception:
                self.logger.exception("Encountered exception while closing Channel.")

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
        self.declare_queue(queue_name, ensure=True)
        return self.consumer_class(self.parameters, queue_name, prefetch, timeout)

    def declare_queue(self, queue_name, *, ensure=False):
        """Declare a queue.  Has no effect if a queue with the given
        name already exists.

        Parameters:
          queue_name(str): The name of the new queue.
          ensure(bool): When True, the queue is created immediately on
            the server.

        Raises:
          ConnectionClosed: When ensure=True if the underlying channel
            or connection fails.
        """
        if queue_name not in self.queues:
            self.emit_before("declare_queue", queue_name)
            self.queues.add(queue_name)
            self.queues_pending.add(queue_name)
            self.emit_after("declare_queue", queue_name)

            delayed_name = dq_name(queue_name)
            self.delay_queues.add(delayed_name)
            self.emit_after("declare_delay_queue", delayed_name)

        if ensure:
            self._ensure_queue(queue_name)

    def _ensure_queue(self, queue_name):
        attempts = 1
        while True:
            try:
                if queue_name in self.queues_pending:
                    self._declare_queue(queue_name)
                    self._declare_dq_queue(queue_name)
                    self._declare_xq_queue(queue_name)
                    self.queues_pending.discard(queue_name)

                break
            except (pika.exceptions.AMQPConnectionError,
                    pika.exceptions.AMQPChannelError) as e:  # pragma: no cover
                # Delete the channel and the connection so that the next
                # caller may initiate new ones of each.
                del self.connection

                attempts += 1
                if attempts > MAX_DECLARE_ATTEMPTS:
                    raise ConnectionClosed(e) from None

                self.logger.debug(
                    "Retrying declare due to closed connection. [%d/%d]",
                    attempts, MAX_DECLARE_ATTEMPTS,
                )

    def _build_queue_arguments(self, queue_name):
        arguments = {
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": xq_name(queue_name),
        }
        if self.max_priority:
            arguments["x-max-priority"] = self.max_priority

        return arguments

    def _declare_queue(self, queue_name):
        arguments = self._build_queue_arguments(queue_name)
        return self.channel.queue_declare(queue=queue_name, durable=True, arguments=arguments)

    def _declare_dq_queue(self, queue_name):
        arguments = self._build_queue_arguments(queue_name)
        return self.channel.queue_declare(queue=dq_name(queue_name), durable=True, arguments=arguments)

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
        self.declare_queue(queue_name, ensure=True)

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
                self.logger.debug("Enqueueing message %r on queue %r.", message.message_id, queue_name)
                self.emit_before("enqueue", message, delay)
                self.channel.basic_publish(
                    exchange="",
                    routing_key=queue_name,
                    body=message.encode(),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        priority=message.options.get("broker_priority"),
                    ),
                )
                self.emit_after("enqueue", message, delay)
                return message

            except (pika.exceptions.AMQPConnectionError,
                    pika.exceptions.AMQPChannelError) as e:
                # Delete the channel and the connection so that the
                # next caller/attempt may initiate new ones of each.
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
            if queue_name not in self.queues_pending:
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


def URLRabbitmqBroker(url, *, middleware=None):
    """Alias for the RabbitMQ broker that takes a connection URL as a
    positional argument.

    Parameters:
      url(str): A connection string.
      middleware(list[Middleware]): The middleware to add to this
        broker.
    """
    warnings.warn(
        "Use RabbitmqBroker with the 'url' parameter instead of URLRabbitmqBroker.",
        DeprecationWarning, stacklevel=2,
    )
    return RabbitmqBroker(url=url, middleware=middleware)


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
            self._nack(message._tag)
        except (pika.exceptions.AMQPConnectionError,
                pika.exceptions.AMQPChannelError) as e:
            raise ConnectionClosed(e) from None
        except KeyError:
            self.logger.warning("Failed to nack message: not in known tags.")
        except Exception:  # pragma: no cover
            self.logger.warning("Failed to nack message.", exc_info=True)

    def _nack(self, tag):
        self.connection.add_callback_threadsafe(
            partial(self.channel.basic_nack, tag, requeue=False),
        )

    def requeue(self, messages):
        """RabbitMQ automatically re-enqueues unacked messages when
        consumers disconnect so this is a no-op.
        """

    def __next__(self):
        try:
            method, properties, body = next(self.iterator)
            if method is None:
                return None
        except (AssertionError,
                pika.exceptions.AMQPConnectionError,
                pika.exceptions.AMQPChannelError) as e:
            raise ConnectionClosed(e) from None

        try:
            message = Message.decode(body)
        except DecodeError:
            self.logger.exception("Failed to decode message using encoder %r.", get_encoder())
            self._nack(method.delivery_tag)
            return None

        rmq_message = _RabbitmqMessage(
            method.redelivered,
            method.delivery_tag,
            message,
        )
        self.known_tags.add(method.delivery_tag)
        return rmq_message

    def close(self):
        try:
            # Closing the connection doesn't wait for all callbacks to
            # finish processing so we enqueue a final callback and
            # wait for it to finish before closing the connection.
            # Assumes callbacks are called in order (they should be).
            all_callbacks_handled = Event()
            self.connection.add_callback_threadsafe(all_callbacks_handled.set)
            while not all_callbacks_handled.is_set():
                self.connection.sleep(0)
        except Exception:
            self.logger.exception(
                "Failed to wait for all callbacks to complete.  This "
                "can happen when the RabbitMQ server is suddenly "
                "restarted."
            )

        try:
            self.channel.close()
            self.connection.close()
        except (AssertionError,
                pika.exceptions.AMQPConnectionError,
                pika.exceptions.AMQPChannelError) as e:
            raise ConnectionClosed(e) from None


class _RabbitmqMessage(MessageProxy):
    def __init__(self, redelivered, tag, message):
        super().__init__(message)

        self.redelivered = redelivered
        self._tag = tag
