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

from __future__ import annotations

import logging
import os
import time
from functools import partial
from itertools import chain
from queue import Empty, Queue
from threading import Event, Lock, Thread, local
from typing import Any, Optional, Union

import pika

from ..broker import Broker, Consumer, MessageProxy
from ..common import current_millis, dq_name, q_name, xq_name
from ..errors import ConnectionClosed, DecodeError, QueueJoinTimeout
from ..logging import get_logger
from ..message import Message, get_encoder
from ..middleware import Middleware

#: The maximum amount of time a message can be in the dead letter queue.
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

      To support queued message priorities, provide a ``max_priority``...

      >>> broker = RabbitmqBroker(url="...", max_priority=5)

      ... then enqueue messages with the ``broker_priority`` option:

      >>> broker.enqueue(an_actor.message_with_options(
      ...    broker_priority=5,
      ... ))

      ``broker_priority`` can also be provided to ``send_with_options``:

      >>> an_actor.send_with_options(
      ...    broker_priority=5,
      ... )

    The ``broker_priority`` provided should have a value between 0 and ``max_priority``, inclusive.
    Messages without a priority are treated as priority 0.
    RabbitMQ treats higher numbers as higher priorities.

    Note:
        This the **opposite** to the Dramatiq actor ``priority`` option.
        (where lower numbers are higher priorities).

    See also:
      ConnectionParameters_ for a list of all the available connection
      parameters.

    Parameters:
      confirm_delivery(bool): Wait for RabbitMQ to confirm that
        messages have been committed on every call to enqueue.
        This must be enabled for Dramatiq to detect and re-declare
        missing queues when enqueing messages.
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

    .. _ConnectionParameters: https://pika.readthedocs.io/en/stable/modules/parameters.html
    """

    def __init__(
        self,
        *,
        confirm_delivery: bool = False,
        url: Optional[Union[str, list[str]]] = None,
        middleware: Optional[list[Middleware]] = None,
        max_priority: Optional[int] = None,
        parameters: Optional[list[dict[str, Any]]] = None,
        **kwargs: Any,
    ):
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
        self.connections: set[pika.BlockingConnection] = set()
        self.channels: set[pika.BlockingChannel] = set()
        # 'queues' is the set of Queues declared on the Broker. These are created lazily in RabbitMQ when required.
        # Note 'queues' should only contain 'canonical' queue names (not delayed or dead-letter queues).
        self.queues: set[str] = set()
        # 'pending_queues' is the Queues that may not exist in RabbitMQ because we haven't attempted to create them yet.
        # Also, should only contain 'canonical' queue names.
        self.queues_pending: set[str] = set()
        self.state = local()
        self._consumer_connection: Optional[_ConsumerSharedConnection] = None
        self._consumer_connection_lock = Lock()

    @property
    def consumer_class(self):
        return _RabbitmqConsumer

    def _get_consumer_connection(self):
        """The connection shared by all of this broker's consumers.

        Each consumer gets its own channel on this connection, so the
        connection count per worker process stays constant no matter how
        many queues are consumed.
        """
        with self._consumer_connection_lock:
            if self._consumer_connection is None:
                self._consumer_connection = _ConsumerSharedConnection(self)
            return self._consumer_connection

    @property
    def connection(self):
        """The :class:`pika.BlockingConnection` for the current
        thread.  This property may change without notice.
        """
        connection = getattr(self.state, "connection", None)
        if connection is None:
            connection = self.state.connection = pika.BlockingConnection(parameters=self.parameters)
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

    def _ignore_pika_logs(self) -> None:
        """Ensures that pika logs are filtered.

        The main thread may keep connections open for a long time
        w/o publishing heartbeats, which means that they'll end up
        being closed by the time the broker is closed.  When that
        happens, pika logs a bunch of scary stuff so we want to
        filter that out.
        """

        logging_filter = _IgnoreScaryLogs()
        ignored_loggers = ["pika.adapters.base_connection", "pika.adapters.blocking_connection"]

        # Make sure the filter is added only once.
        for logger_name in ignored_loggers:
            ignored_logger = logging.getLogger(logger_name)
            if not any(isinstance(f, _IgnoreScaryLogs) for f in ignored_logger.filters):
                ignored_logger.addFilter(logging_filter)

    def close(self) -> None:
        """Close all open RabbitMQ connections."""

        self._ignore_pika_logs()

        with self._consumer_connection_lock:
            if self._consumer_connection is not None:
                self._consumer_connection.stop()
                self._consumer_connection = None

        self.logger.debug("Closing channels and connections...")
        for channel_or_conn in chain(self.channels, self.connections):
            try:
                channel_or_conn.close()
            except pika.exceptions.AMQPError:
                pass

            except Exception:  # pragma: no cover
                self.logger.debug(
                    "Encountered an error while closing %r.",
                    channel_or_conn,
                    exc_info=True,
                )
        self.logger.debug("Channels and connections closed.")

    def consume(self, queue_name: str, prefetch: int = 1, timeout: int = 5000) -> Consumer:
        """Create a new consumer for a queue.

        Parameters:
          queue_name(str): The queue to consume.
          prefetch(int): The number of messages to prefetch.
          timeout(int): The idle timeout in milliseconds.

        Returns:
          Consumer: A consumer that retrieves messages from RabbitMQ.
        """
        self.declare_queue(queue_name, ensure=True)
        # Drop the connection the declare just used: consume() runs on consumer
        # threads, which don't publish, so it would sit idle on each of them forever.
        del self.connection
        return self.consumer_class(self, queue_name, prefetch, timeout)

    def declare_queue(self, queue_name: str, *, ensure: bool = False) -> None:
        """Declare a queue.  Has no effect if a queue with the given
        name already exists.

        Parameters:
          queue_name(str): The name of the new queue.
          ensure(bool): When True, the queue is created on the server,
            if necessary.

        Raises:
          ConnectionClosed: When ensure=True if the underlying channel
            or connection fails.
        """
        # Note: queue_name can be a canonical queue or a delayed queue.
        canonical_queue_name = q_name(queue_name)
        if canonical_queue_name not in self.queues:
            self.emit_before("declare_queue", canonical_queue_name)
            self.queues.add(canonical_queue_name)
            self.queues_pending.add(canonical_queue_name)
            self.emit_after("declare_queue", canonical_queue_name)

            delayed_name = dq_name(queue_name)
            self.delay_queues.add(delayed_name)
            self.emit_after("declare_delay_queue", delayed_name)

        if ensure:
            self._ensure_queue(canonical_queue_name)

    def _ensure_queue(self, canonical_queue_name):
        attempts = 0
        while True:
            try:
                if canonical_queue_name in self.queues_pending:
                    self._declare_queue(canonical_queue_name)
                    self._declare_dq_queue(canonical_queue_name)
                    self._declare_xq_queue(canonical_queue_name)
                    self.queues_pending.discard(canonical_queue_name)

                break
            except (
                pika.exceptions.AMQPConnectionError,
                pika.exceptions.AMQPChannelError,
            ) as e:  # pragma: no cover
                # Delete the channel and the connection so that the next
                # caller may initiate new ones of each.
                del self.connection

                attempts += 1
                if attempts >= MAX_DECLARE_ATTEMPTS:
                    raise ConnectionClosed(e) from None

                self.logger.debug(
                    "Retrying declare due to closed connection. [%d/%d] attempts made so far.",
                    attempts,
                    MAX_DECLARE_ATTEMPTS,
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
        return self.channel.queue_declare(
            queue=xq_name(queue_name),
            durable=True,
            arguments={
                # This HAS to be a static value since messages are expired
                # in order inside of RabbitMQ (head-first).
                "x-message-ttl": DEAD_MESSAGE_TTL,
            },
        )

    def enqueue(self, message: Message, *, delay: Optional[int] = None) -> Message:
        """Enqueue a message.

        Parameters:
          message(Message): The message to enqueue.
          delay(int): The minimum amount of time, in milliseconds, to
            delay the message by.

        Raises:
          ConnectionClosed: If the underlying channel or connection
            has been closed.
        """
        canonical_queue_name = message.queue_name
        queue_name = canonical_queue_name

        if delay is not None:
            queue_name = dq_name(queue_name)
            message_eta = current_millis() + delay
            message = message.copy(
                queue_name=queue_name,
                options={
                    "eta": message_eta,
                },
            )

        attempts = 0
        while True:
            try:
                self.declare_queue(canonical_queue_name, ensure=True)
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
                    # mandatory flag ensures UnroutableError is raised if message could not be routed to a queue,
                    # but it only works when confirm_delivery is turned on, so only set it when that is the case.
                    # https://www.rabbitmq.com/docs/publishers#unroutable
                    mandatory=self.confirm_delivery,
                )
                self.emit_after("enqueue", message, delay)
                return message

            except (
                pika.exceptions.AMQPConnectionError,
                pika.exceptions.AMQPChannelError,
            ) as e:
                # Delete the channel and the connection so that the
                # next caller/attempt may initiate new ones of each.
                del self.connection

                # If the queue disappears, add it to the set of pending queues
                # so that it can be redeclared on retry or the next time
                # a message is enqueued.
                # Note this only happens when confirm_delivery is enabled.
                if isinstance(e, pika.exceptions.UnroutableError):
                    self.queues_pending.add(q_name(queue_name))

                attempts += 1
                if attempts >= MAX_ENQUEUE_ATTEMPTS:
                    raise ConnectionClosed(e) from None

                self.logger.debug(
                    "Retrying enqueue due to closed connection. [%d/%d] attempts made so far.",
                    attempts,
                    MAX_ENQUEUE_ATTEMPTS,
                )

    def get_declared_queues(self) -> set[str]:
        """Get all declared queues.

        Returns:
          set[str]: The names of all the queues declared so far on
          this Broker.
        """
        return self.queues.copy()

    def get_queue_message_counts(self, queue_name: str) -> tuple[int, int, int]:
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

    def flush(self, queue_name: str) -> None:
        """Drop all the messages from a queue.

        Parameters:
          queue_name(str): The queue to flush.
        """
        # Purge messages from all queues, even from delayed queues and dead letter queues.
        # The purge operation fails with an exception if the queue doesn't exist. The the underlying
        # RabbitMQ channel is closed by the broker. We have to reopen the channel to continue
        # purging other queues.
        for name in (queue_name, dq_name(queue_name), xq_name(queue_name)):
            try:
                self.channel.queue_purge(name)
            except pika.exceptions.AMQPChannelError:
                del self.channel

    def flush_all(self) -> None:
        """Drop all messages from all declared queues."""
        for queue_name in self.queues:
            self.flush(queue_name)

    def join(
        self, queue_name: str, min_successes: int = 10, idle_time: int = 100, *, timeout: Optional[int] = None
    ) -> None:
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


class _ConsumerSharedConnection:
    """The one connection all of a broker's consumers share.

    pika connections aren't thread safe, so a dedicated I/O thread owns the
    connection and everyone else interacts with it in exactly two ways:
    deliveries are dispatched from the I/O thread into per-consumer buffers,
    and consumers marshal their channel operations (subscribe, ack, nack,
    close) onto the I/O thread with add_callback_threadsafe.

    A consumer whose channel or connection dies is handed the error through
    its buffer and never comes back: its ConsumerThread sees ConnectionClosed
    and restarts with a fresh consumer.
    """

    # How long a consumer waits for its subscription to become live.
    subscribe_timeout = 30

    def __init__(self, broker):
        self.broker = broker
        self.logger = get_logger(__name__, type(self))
        self.connection = None
        self._consumers = set()
        self._requests = Queue()
        self._stopped = Event()
        self._thread = Thread(target=self._run, daemon=True, name="dramatiq-rabbitmq-consumer-io")
        self._thread.start()

    def subscribe(self, consumer):
        """Open a channel for the consumer and start consuming its queue.
        Blocks until the subscription is live.
        """
        if not self._thread.is_alive():
            raise pika.exceptions.AMQPConnectionError("the shared consumer connection is stopped")

        ready = Event()
        error = []

        def request():
            if consumer.closed:  # the consumer gave up waiting
                return
            try:
                if self.connection is None:
                    raise pika.exceptions.AMQPConnectionError("the shared consumer connection is down")
                channel = self.connection.channel()
                channel.basic_qos(prefetch_count=consumer.prefetch)
                channel.add_on_cancel_callback(partial(self._on_cancel, consumer))
                consumer.channel = channel
                channel.basic_consume(consumer.queue_name, partial(self._on_message, consumer))
                self._consumers.add(consumer)
            except Exception as e:
                error.append(e)
            finally:
                ready.set()

        self._requests.put(request)
        self._wake()
        if not ready.wait(self.subscribe_timeout):
            # The request may still run later.  The closed flag turns it into
            # a no-op and the unsubscribe cleans up in case it just ran.
            consumer.closed = True
            self.unsubscribe(consumer)
            raise pika.exceptions.AMQPConnectionError("timed out waiting for the shared consumer connection")
        if error:
            raise error[0]

    def call_soon(self, callback):
        """Run a channel operation on the I/O thread, in order with deliveries and acks."""
        connection = self.connection
        if connection is None or not connection.is_open or not self._thread.is_alive():
            raise pika.exceptions.AMQPConnectionError("the shared consumer connection is down")
        connection.add_callback_threadsafe(callback)

    def unsubscribe(self, consumer):
        """Close the consumer's channel. Blocks until it is closed, so
        unacked deliveries are back in their queue by the time this returns.
        """
        done = Event()

        def request():
            try:
                self._consumers.discard(consumer)
                if consumer.channel is not None and consumer.channel.is_open:
                    consumer.channel.close()
            except pika.exceptions.AMQPChannelError:  # pragma: no cover
                self.logger.debug("Encountered an error while closing a consumer channel.", exc_info=True)
            finally:
                done.set()

        try:
            # Through the connection so it runs after the consumer's pending acks.
            self.call_soon(request)
        except pika.exceptions.AMQPConnectionError:
            return  # the connection is gone and took the channel with it
        done.wait(self.subscribe_timeout)

    def stop(self):
        self._stopped.set()
        self._thread.join(timeout=30)

    def _wake(self):
        try:
            connection = self.connection
            if connection is not None and connection.is_open:
                connection.add_callback_threadsafe(self._drain_requests)
        except pika.exceptions.ConnectionWrongStateError:  # pragma: no cover
            pass  # the request will be drained by the main loop instead

    def _run(self):
        backoff = 0.5
        while not self._stopped.is_set():
            try:
                if self.connection is None:
                    self.connection = pika.BlockingConnection(parameters=self.broker.parameters)
                    backoff = 0.5
                self.connection.process_data_events(time_limit=1.0)
                self._drain_requests()
            except Exception as e:
                # If this thread dies, every consumer starves without an error, so
                # anything raised here has to turn into a reconnect instead.
                if self._stopped.is_set():
                    break
                self.logger.warning("Consumer connection lost, reconnecting in %.01fs.", backoff, exc_info=True)
                self._fail_consumers(e)
                self.connection = None
                self._stopped.wait(backoff)
                backoff = min(backoff * 2, 8)
        self._close_connection()

    def _drain_requests(self):
        while True:
            try:
                request = self._requests.get_nowait()
            except Empty:
                return
            request()

    def _on_message(self, consumer, channel, method, properties, body):
        consumer.buffer.put((method, body))

    def _on_cancel(self, consumer, method):
        # The broker cancelled the consumer, most likely because its queue was
        # deleted. Report it as a 404 so the queue gets redeclared on restart.
        self._consumers.discard(consumer)
        consumer.buffer.put(pika.exceptions.ChannelClosedByBroker(404, "consumer cancelled by the broker"))

    def _fail_consumers(self, error):
        consumers, self._consumers = self._consumers, set()
        for consumer in consumers:
            # Deliveries still sitting in the buffer were requeued by RabbitMQ when the connection died,
            # so processing them now would process them twice.
            while True:
                try:
                    consumer.buffer.get_nowait()
                except Empty:
                    break
            consumer.buffer.put(error)

    def _close_connection(self):
        connection, self.connection = self.connection, None
        if connection is None:
            return
        try:
            # Closing the connection doesn't wait for all callbacks to
            # finish processing so we enqueue a final callback and
            # wait for it to finish before closing the connection.
            # Assumes callbacks are called in order (they should be).
            all_callbacks_handled = Event()
            connection.add_callback_threadsafe(all_callbacks_handled.set)
            while not all_callbacks_handled.is_set():
                connection.sleep(0)
            connection.close()
        except Exception:
            self.logger.exception(
                "Failed to wait for all callbacks to complete.  This "
                "can happen when the RabbitMQ server is suddenly "
                "restarted."
            )


class _RabbitmqConsumer(Consumer):
    def __init__(self, broker, queue_name, prefetch, timeout):
        self.broker = broker
        self.queue_name = queue_name
        self.prefetch = prefetch
        self.timeout = timeout
        self.logger = get_logger(__name__, type(self))

        # Deliveries (and errors) handed over from the shared connection's I/O thread.
        self.buffer = Queue()
        self.channel = None
        self.closed = False

        # We need to keep track of known delivery tags so that
        # when connection errors occur and the consumer is reset,
        # we don't attempt to send invalid tags to Rabbit since
        # pika doesn't handle this very well.
        self.known_tags = set()

        try:
            self.shared_connection = broker._get_consumer_connection()
            self.shared_connection.subscribe(self)
        except (
            pika.exceptions.AMQPConnectionError,
            pika.exceptions.AMQPChannelError,
        ) as e:
            self.closed = True
            if getattr(e, "reply_code", None) == 404:
                self.broker.queues_pending.add(q_name(self.queue_name))
            raise ConnectionClosed(e) from None

    def ack(self, message):
        try:
            self.known_tags.remove(message._tag)
            self.shared_connection.call_soon(
                partial(_ack_if_open, self.channel, message._tag),
            )
        except (
            pika.exceptions.AMQPConnectionError,
            pika.exceptions.AMQPChannelError,
        ) as e:
            raise ConnectionClosed(e) from None
        except KeyError:
            self.logger.warning("Failed to ack message: not in known tags.")
        except Exception:  # pragma: no cover
            self.logger.warning("Failed to ack message.", exc_info=True)

    def nack(self, message):
        try:
            self.known_tags.remove(message._tag)
            self._nack(message._tag)
        except (
            pika.exceptions.AMQPConnectionError,
            pika.exceptions.AMQPChannelError,
        ) as e:
            raise ConnectionClosed(e) from None
        except KeyError:
            self.logger.warning("Failed to nack message: not in known tags.")
        except Exception:  # pragma: no cover
            self.logger.warning("Failed to nack message.", exc_info=True)

    def _nack(self, tag):
        self.shared_connection.call_soon(
            partial(_nack_if_open, self.channel, tag),
        )

    def requeue(self, messages):
        """RabbitMQ automatically re-enqueues unacked messages when
        consumers disconnect so this is a no-op.
        """

    def __next__(self):
        try:
            item = self.buffer.get(timeout=self.timeout / 1000)
        except Empty:
            return None

        if isinstance(item, Exception):
            # If the queue disappears, add it to the set of pending queues
            # so that it can be redeclared on when the consumer restarts.
            if getattr(item, "reply_code", None) == 404:
                self.broker.queues_pending.add(q_name(self.queue_name))
            raise ConnectionClosed(item) from None

        method, body = item
        try:
            message = Message.decode(body)
        except DecodeError:
            self.logger.exception("Failed to decode message using encoder %r.", get_encoder())
            try:
                self._nack(method.delivery_tag)
            except pika.exceptions.AMQPConnectionError:
                pass  # The connection died, so RabbitMQ will redeliver.
            return None

        rmq_message = _RabbitmqMessage(
            method.redelivered,
            method.delivery_tag,
            message,
        )
        self.known_tags.add(method.delivery_tag)
        return rmq_message

    def close(self):
        self.closed = True
        self.shared_connection.unsubscribe(self)


def _ack_if_open(channel, tag):
    # A dead channel means RabbitMQ already requeued the delivery, so its tag
    # must not be sent to whatever channel replaced it.
    if channel.is_open:
        channel.basic_ack(tag)


def _nack_if_open(channel, tag):
    if channel.is_open:
        channel.basic_nack(tag, requeue=False)


class _RabbitmqMessage(MessageProxy):
    def __init__(self, redelivered, tag, message):
        super().__init__(message)

        self.redelivered = redelivered
        self._tag = tag
