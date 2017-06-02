import logging

from .errors import ActorNotFound

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

        for actor_name in self.get_declared_actors():
            middleware.after_declare_actor(actor_name)

        for queue_name in self.get_declared_queues():
            middleware.after_declare_queue(queue_name)

    def close(self):
        """Close this broker and perform any necessary cleanup actions.
        """

    def consume(self, queue_name, timeout=30):  # pragma: no cover
        """Get an iterator that consumes messages off of the queue.

        Raises:
          QueueNotFound: If the given queue was never declared.

        Parameters:
          queue_name(str): The name of the queue to consume messages off of.
          timeout(int)

        Returns:
          Consumer
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
          message(Message)
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
            self._emit_before("acknowledge", message)
            message.acknowledge()
            self._emit_after("acknowledge", message)


class Consumer:
    """Consumers iterate over messages on a queue.
    """

    def __iter__(self):
        return self

    def __next__(self):
        raise NotImplementedError

    def close(self):
        """Close this consumer and perform any necessary cleanup actions.
        """
