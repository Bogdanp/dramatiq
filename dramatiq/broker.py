# This file is a part of Dramatiq.
#
# Copyright (C) 2017,2018,2019,2020 CLEARTYPE SRL <bogdan@cleartype.io>
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

from typing import Optional, cast

from .errors import ActorNotFound
from .logging import get_logger
from .middleware import MiddlewareError, default_middleware
from .results import Results

#: The global broker instance.
global_broker: Optional["Broker"] = None


def get_broker() -> "Broker":
    """Get the global broker instance.

    If no global broker is set, a RabbitMQ broker will be returned.
    If the RabbitMQ dependencies are not installed, a Redis broker
    will be returned.

    Returns:
      Broker: The default Broker.
    """
    global global_broker
    if global_broker is None:
        # RabbitMQ will be tried first, but its dependencies might not
        # be installed if the user only installed the [redis] extras.
        try:
            from .brokers.rabbitmq import RabbitmqBroker

            set_broker(RabbitmqBroker(
                host="127.0.0.1",
                port=5672,
                heartbeat=5,
                connection_attempts=5,
                blocked_connection_timeout=30,
            ))
        except ImportError:
            # Fall back to the Redis broker.
            from .brokers.redis import RedisBroker

            set_broker(RedisBroker())
    global_broker = cast("Broker", global_broker)
    return global_broker


def set_broker(broker: "Broker"):
    """Configure the global broker instance.

    Parameters:
      broker(Broker): The broker instance to use by default.
    """
    global global_broker
    global_broker = broker


class Broker:
    """Base class for broker implementations.

    Parameters:
      middleware(list[Middleware]): The set of middleware that apply
        to this broker.  If you supply this parameter, you are
        expected to declare *all* middleware.  Most of the time,
        you'll want to use :meth:`.add_middleware` instead.

    Attributes:
      actor_options(set[str]): The names of all the options actors may
        overwrite when they are declared.
    """

    def __init__(self, middleware=None):
        self.logger = get_logger(__name__, type(self))
        self.actors = {}
        self.queues = {}
        self.delay_queues = set()

        self.actor_options = set()
        self.middleware = []

        if middleware is None:
            middleware = [m() for m in default_middleware]

        for m in middleware:
            self.add_middleware(m)

    def emit_before(self, signal, *args, **kwargs):
        signal = "before_" + signal
        for middleware in self.middleware:
            try:
                getattr(middleware, signal)(self, *args, **kwargs)
            except MiddlewareError:
                raise
            except Exception:
                self.logger.critical("Unexpected failure in %s of %r.", signal, middleware, exc_info=True)

    def emit_after(self, signal, *args, **kwargs):
        signal = "after_" + signal
        for middleware in reversed(self.middleware):
            try:
                getattr(middleware, signal)(self, *args, **kwargs)
            except Exception:
                self.logger.critical("Unexpected failure in %s of %r.", signal, middleware, exc_info=True)

    def add_middleware(self, middleware, *, before=None, after=None):
        """Add a middleware object to this broker.  The middleware is
        appended to the end of the middleware list by default.

        You can specify another middleware (by class) as a reference
        point for where the new middleware should be added.

        Parameters:
          middleware(Middleware): The middleware.
          before(type): Add this middleware before a specific one.
          after(type): Add this middleware after a specific one.

        Raises:
          ValueError: When either ``before`` or ``after`` refer to a
            middleware that hasn't been registered yet.
        """
        assert not (before and after), \
            "provide either 'before' or 'after', but not both"

        if before or after:
            for i, m in enumerate(self.middleware):  # noqa
                if isinstance(m, before or after):
                    break
            else:
                raise ValueError("Middleware %r not found" % (before or after))

            if before:
                self.middleware.insert(i, middleware)
            else:
                self.middleware.insert(i + 1, middleware)
        else:
            self.middleware.append(middleware)

        self.actor_options |= middleware.actor_options

        for actor_name in self.get_declared_actors():
            middleware.after_declare_actor(self, actor_name)

        for queue_name in self.get_declared_queues():
            middleware.after_declare_queue(self, queue_name)

        for queue_name in self.get_declared_delay_queues():
            middleware.after_declare_delay_queue(self, queue_name)

    def close(self):
        """Close this broker and perform any necessary cleanup actions.
        """

    def consume(self, queue_name, prefetch=1, timeout=30000):  # pragma: no cover
        """Get an iterator that consumes messages off of the queue.

        Raises:
          QueueNotFound: If the given queue was never declared.

        Parameters:
          queue_name(str): The name of the queue to consume messages off of.
          prefetch(int): The number of messages to prefetch per consumer.
          timeout(int): The amount of time in milliseconds to idle for.

        Returns:
          Consumer: A message iterator.
        """
        raise NotImplementedError

    def declare_actor(self, actor):  # pragma: no cover
        """Declare a new actor on this broker.  Declaring an Actor
        twice replaces the first actor with the second by name.

        Parameters:
          actor(Actor): The actor being declared.
        """
        self.emit_before("declare_actor", actor)
        self.declare_queue(actor.queue_name)
        self.actors[actor.actor_name] = actor
        self.emit_after("declare_actor", actor)

    def declare_queue(self, queue_name):  # pragma: no cover
        """Declare a queue on this broker.  This method must be
        idempotent.

        Parameters:
          queue_name(str): The name of the queue being declared.
        """
        raise NotImplementedError

    def enqueue(self, message, *, delay=None):  # pragma: no cover
        """Enqueue a message on this broker.

        Parameters:
          message(Message): The message to enqueue.
          delay(int): The number of milliseconds to delay the message for.

        Returns:
          Message: Either the original message or a copy of it.
        """
        raise NotImplementedError

    def get_actor(self, actor_name):  # pragma: no cover
        """Look up an actor by its name.

        Parameters:
          actor_name(str): The name to look up.

        Raises:
          ActorNotFound: If the actor was never declared.

        Returns:
          Actor: The actor.
        """
        try:
            return self.actors[actor_name]
        except KeyError:
            raise ActorNotFound(actor_name) from None

    def get_declared_actors(self):  # pragma: no cover
        """Get all declared actors.

        Returns:
          set[str]: The names of all the actors declared so far on
          this Broker.
        """
        return set(self.actors.keys())

    def get_declared_queues(self):  # pragma: no cover
        """Get all declared queues.

        Returns:
          set[str]: The names of all the queues declared so far on
          this Broker.
        """
        return set(self.queues.keys())

    def get_declared_delay_queues(self):  # pragma: no cover
        """Get all declared delay queues.

        Returns:
          set[str]: The names of all the delay queues declared so far
          on this Broker.
        """
        return self.delay_queues.copy()

    def get_results_backend(self):
        """Get the backend of the Results middleware.

        Raises:
          RuntimeError: If the broker doesn't have a results backend.

        Returns:
          ResultBackend: The backend.
        """
        for middleware in self.middleware:
            if isinstance(middleware, Results):
                return middleware.backend
        else:
            raise RuntimeError("The broker doesn't have a results backend.")

    def flush(self, queue_name):  # pragma: no cover
        """Drop all the messages from a queue.

        Parameters:
          queue_name(str): The name of the queue to flush.
        """
        raise NotImplementedError()

    def flush_all(self):  # pragma: no cover
        """Drop all messages from all declared queues.
        """
        raise NotImplementedError()

    def join(self, queue_name, *, timeout=None):  # pragma: no cover
        """Wait for all the messages on the given queue to be
        processed.  This method is only meant to be used in tests to
        wait for all the messages in a queue to be processed.

        Subclasses that implement this function may add parameters.

        Parameters:
          queue_name(str): The queue to wait on.
          timeout(Optional[int]): The max amount of time, in
            milliseconds, to wait on this queue.
        """
        raise NotImplementedError()


class Consumer:
    """Consumers iterate over messages on a queue.

    Consumers and their MessageProxies are *not* thread-safe.
    """

    def __iter__(self):  # pragma: no cover
        """Returns this instance as a Message iterator.
        """
        return self

    def ack(self, message):  # pragma: no cover
        """Acknowledge that a message has been processed, removing it
        from the broker.

        Parameters:
          message(MessageProxy): The message to acknowledge.
        """
        raise NotImplementedError

    def nack(self, message):  # pragma: no cover
        """Move a message to the dead-letter queue.

        Parameters:
          message(MessageProxy): The message to reject.
        """
        raise NotImplementedError

    def requeue(self, messages):  # pragma: no cover
        """Move unacked messages back to their queues.  This is called
        by consumer threads when they fail or are shut down.  The
        default implementation does nothing.

        Parameters:
          messages(list[MessageProxy]): The messages to requeue.
        """

    def __next__(self):  # pragma: no cover
        """Retrieve the next message off of the queue.  This method
        blocks until a message becomes available.

        Returns:
          MessageProxy: A transparent proxy around a Message that can
          be used to acknowledge or reject it once it's done being
          processed.
        """
        raise NotImplementedError

    def close(self):
        """Close this consumer and perform any necessary cleanup actions.
        """


class MessageProxy:
    """Base class for messages returned by :meth:`Broker.consume`.
    """

    def __init__(self, message):
        self.failed = False
        self._message = message
        self._exception = None

    def stuff_exception(self, exception):
        """Stuff an exception into this message.
        """
        self._exception = exception

    def clear_exception(self):
        """Remove the exception from this message.
        """
        del self._exception

    def fail(self):
        """Mark this message for rejection.
        """
        self.failed = True

    def __getattr__(self, name):
        return getattr(self._message, name)

    def __str__(self):
        return str(self._message)

    def __lt__(self, other):
        # This can get called if two messages have the same priority
        # in a queue.  If that's the case, we don't care which runs
        # first.
        return True

    def __eq__(self, other):
        if isinstance(other, MessageProxy):
            return self._message == other._message
        return self._message == other
