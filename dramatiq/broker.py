import logging

#: The global broker instance.
global_broker = None


def get_broker():
    """Get the global broker instance.  If no global broker is set,
    this initializes a RabbitmqBroker and returns that.
    """
    global global_broker
    if global_broker is None:
        from .brokers import RabbitmqBroker
        set_broker(RabbitmqBroker())
    return global_broker


def set_broker(broker):
    """Configure the global broker instance.

    Parameters:
      broker(Broker)
    """
    global global_broker
    global_broker = broker


class Broker:
    """Base class for broker implementations.

    Parameters:
      middleware(list[Middleware]): The set of middleware that apply
        to this broker.
    """

    def __init__(self, middleware=None):
        self.logger = logging.getLogger(type(self).__name__)
        self.middleware = middleware or []
        self.actors = {}
        self.queues = {}

    def _emit_before(self, signal, *args, **kwargs):
        for middleware in self.middleware:
            getattr(middleware, f"before_{signal}")(*args, **kwargs)

    def _emit_after(self, signal, *args, **kwargs):
        for middleware in reversed(self.middleware):
            getattr(middleware, f"after_{signal}")(*args, **kwargs)

    def add_middleware(self, middleware):
        """Add a middleware object to this broker.

        Parameters:
          middleware(Middleware)
        """
        self.middleware.append(middleware)

    def acknowledge(self, queue_name, ack_id):  # pragma: no cover
        """Acknowledge that a message is done processing.

        Raises:
          QueueNotFound: If the given queue was never declared.

        Parameters:
          queue_name(str): The name of the queue the message was received on.
          ack_id(str): The acknowledgement nonce for a particular message.
        """
        raise NotImplementedError

    def close(self):
        """Stop this broker.
        """
        raise NotImplementedError

    def declare_actor(self, actor):  # pragma: no cover
        """Declare a new actor on this broker.  Declaring an Actor
        twice replaces the first actor with the second by name.

        Parameters:
          actor(Actor)
        """
        self._emit_before("declare_actor", actor)
        self.declare_queue(actor.queue_name)
        self.actors[actor.actor_name] = actor
        self._emit_after("declare_actor", actor)

    def declare_queue(self, queue_name):  # pragma: no cover
        """Declare a queue on this broker.  This method must be
        idempotent.

        Parameters:
          queue_name(str)
        """
        raise NotImplementedError

    def enqueue(self, message):  # pragma: no cover
        """Enqueue a message on this broker.

        Parameters:
          message(Message)
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

    def get_consumer(self, queue_name, on_message):  # pragma: no cover
        """Get an object that consumes messages from the queue and
        calls on_message for every message that it finds.

        Raises:
          QueueNotFound: If the given queue was never declared.

        Parameters:
          queue_name(str): The name of the queue to consume messages off of.
          on_message(callable): A function to be called whenever a
            message is received.  The function must take two parameters:
            a Message object and an ack_id.

        Returns:
          Consumer: A consumer object.
        """
        raise NotImplementedError

    def get_declared_queues(self):  # pragma: no cover
        """Returns a list of all the named queues declared on this broker.
        """
        return self.queues.keys()

    def process_message(self, message, ack_id):
        """Process a message and then acknowledge it.

        Parameters:
          message(Message)
          ack_id(str)
        """
        try:
            self._emit_before("process_message", message)
            actor = self.get_actor(message.actor_name)
            res = actor(*message.args, **message.kwargs)
            self._emit_after("process_message", message, result=res)

        except BaseException as e:
            self.logger.warning("Failed to process message %r with unhandled exception.", message, exc_info=True)
            self._emit_after("process_message", message, exception=e)

        finally:
            self.logger.debug("Acknowledging message %r.", message.message_id)
            self._emit_before("acknowledge", message, ack_id)
            self.acknowledge(message.queue_name, ack_id)
            self._emit_after("acknowledge", message, ack_id)


class Consumer:
    """Base class for consumer objects.
    """

    def start(self):  # pragma: no cover
        """Start this consumer.
        """
        raise NotImplementedError

    def stop(self):  # pragma: no cover
        """Stop this consumer.
        """
        raise NotImplementedError


class BrokerError(Exception):
    """Base class for broker-related errors.
    """


class ActorNotFound(BrokerError):
    """Raised when a message is sent to an actor that hasn't been declared.
    """


class QueueNotFound(BrokerError):
    """Raised when a message is sent to an queue that hasn't been declared.
    """
