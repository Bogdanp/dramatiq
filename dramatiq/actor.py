from .broker import get_broker
from .message import Message


def actor(fn=None, *, queue_name="default", actor_name=None, broker=None):
    """Declare an Actor.

    Parameters:
      fn(callable)
      queue_name(str)
      actor_name(str)
      broker(Broker)

    Returns:
      Actor
    """
    def decorator(fn):
        nonlocal actor_name, broker
        actor_name = actor_name or f"{fn.__module__}.{fn.__name__}"
        broker = broker or get_broker()
        return Actor(fn, queue_name=queue_name, actor_name=actor_name, broker=broker)

    if fn is None:
        return decorator
    return decorator(fn)


class Actor:
    def __init__(self, fn, *, broker, queue_name, actor_name):
        self.fn = fn
        self.broker = broker
        self.queue_name = queue_name
        self.actor_name = actor_name
        self.broker.declare_actor(self)

    def send(self, *args, **kwargs):
        """Asynchronously send a message to this actor.

        Note:
          All arguments must be JSON-encodable.

        Parameters:
          \*args(tuple): Positional arguments to send to the actor.
          \**kwargs(dict): Keyword arguments to send to the actor.

        Returns:
          Message: The enqueued message.
        """
        return self.send_with_options(args, kwargs)

    def send_with_options(self, args, kwargs, **options):
        """Asynchronously send a message to this actor, along with an
        arbitrary set of processing options for the broker and
        middleware.

        Parameters:
          args(tuple): Positional arguments that are passed to the actor.
          kwargs(dict): Keyword arguments that are passed to the actor.
          \**options(dict): Arbitrary options that are passed to the
            broker and any registered middleware.

        Returns:
          Message: The enqueued message.
        """
        message = Message(
            queue_name=self.queue_name,
            actor_name=self.actor_name,
            args=args, kwargs=kwargs,
            options=options,
        )

        self.broker.enqueue(message)
        return message

    def __call__(self, *args, **kwargs):
        """Synchronously call this actor.

        Parameters:
          \*args: Positional arguments to send to the actor.
          \**kwargs: Keyword arguments to send to the actor.

        Returns:
          Whatever the underlying function backing this actor returns.
        """
        return self.fn(*args, **kwargs)

    def __repr__(self):  # pragma: no cover
        return f"Actor({self.fn!r}, queue_name={self.queue_name!r}, actor_name={self.actor_name!r})"

    def __str__(self):  # pragma: no cover
        return f"Actor({self.actor_name!r})"
