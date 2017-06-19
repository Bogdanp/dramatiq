from .errors import ActorNotFound
from .logging import get_logger
from .middleware import AgeLimit, Prometheus, Retries, TimeLimit

#: The global broker instance.
global_broker = None

#: The list of middleware that are enabled by default.
default_middleware = [Prometheus, AgeLimit, TimeLimit, Retries]


def get_broker():
    """Get the global broker instance.  If no global broker is set,
    this initializes a RabbitmqBroker and returns that.

    Returns:
      Broker: The default Broker.
    """
    global global_broker
    if global_broker is None:
        from .brokers import RabbitmqBroker
        set_broker(RabbitmqBroker())
    return global_broker


def set_broker(broker):
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
    """

    def __init__(self, middleware=None):
        self.logger = get_logger(__name__, type(self))
        self.actors = {}
        self.queues = {}

        self.middleware = middleware or [m() for m in default_middleware]
        self.actor_options = set()
        for middleware in self.middleware:
            self.actor_options |= middleware.actor_options

    def emit_before(self, signal, *args, **kwargs):
        for middleware in self.middleware:
            getattr(middleware, f"before_{signal}")(self, *args, **kwargs)

    def emit_after(self, signal, *args, **kwargs):
        for middleware in reversed(self.middleware):
            getattr(middleware, f"after_{signal}")(self, *args, **kwargs)

    def add_middleware(self, middleware):
        """Add a middleware object to this broker.
        """
        self.middleware.append(middleware)
        self.actor_options |= middleware.actor_options

        for actor_name in self.get_declared_actors():
            middleware.after_declare_actor(self, actor_name)

        for queue_name in self.get_declared_queues():
            middleware.after_declare_queue(self, queue_name)

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
        """
        raise NotImplementedError

    def get_actor(self, actor_name):  # pragma: no cover
        """Look up an actor by its name.

        Raises:
          ActorNotFound: If the actor was never declared.

        Returns:
          Actor: The actor.
        """
        try:
            return self.actors[actor_name]
        except KeyError:
            raise ActorNotFound(actor_name)

    def get_declared_actors(self):  # pragma: no cover
        """Returns a list of all the named actors declared on this broker.
        """
        return self.actors.keys()

    def get_declared_queues(self):  # pragma: no cover
        """Returns a list of all the named queues declared on this broker.
        """
        return self.queues.keys()

    def process_message(self, message):
        """Process a message and then acknowledge it.

        Parameters:
          message(MessageProxy): The message being processed.
        """
        try:
            self.emit_before("process_message", message)
            if message._failed:
                res = None
            else:
                actor = self.get_actor(message.actor_name)
                res = actor(*message.args, **message.kwargs)
            self.emit_after("process_message", message, result=res)

        except BaseException as e:
            self.logger.warning("Failed to process message %r with unhandled exception.", message, exc_info=True)
            self.emit_after("process_message", message, exception=e)

        finally:
            if message._failed:
                self.logger.debug("Rejecting message %r.", message.message_id)
                self.emit_before("reject", message)
                message.reject()
                self.emit_after("reject", message)

            else:
                self.logger.debug("Acknowledging message %r.", message.message_id)
                self.emit_before("acknowledge", message)
                message.acknowledge()
                self.emit_after("acknowledge", message)


class Consumer:
    """Consumers iterate over messages on a queue.
    """

    def __iter__(self):  # pragma: no cover
        """Returns this instance as a Message iterator.
        """
        return self

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
        self._message = message
        self._failed = False

    def acknowledge(self):  # pragma: no cover
        """Acknowledge that this message has been procesed.
        """
        raise NotImplementedError

    def fail(self):
        """Mark this message for rejection.
        """
        self._failed = True

    def reject(self):  # pragma: no cover
        """Reject this message, moving it to the dead letter queue.
        """
        raise NotImplementedError

    def __getattr__(self, name):
        return getattr(self._message, name)

    def __str__(self):
        return str(self._message)

    def __lt__(self, other):
        return self._message < other._message

    def __le__(self, other):
        return self._message <= other._message

    def __gt__(self, other):
        return self._message > other._message

    def __ge__(self, other):
        return self._message >= other._message

    def __eq__(self, other):
        return self._message == other._message

    def __ne__(self, other):
        return self._message != other._message
