import re

from .broker import get_broker
from .message import Message

#: The regular expression that represents valid queue names.
_queue_name_re = re.compile(r"[a-zA-Z_][a-zA-Z0-9_-]*")


def actor(fn=None, *, actor_name=None, queue_name="default", priority=0, broker=None, **options):
    """Declare an Actor.

    Examples:

      >>> import dramatiq

      >>> @dramatiq.actor
      ... def add(x, y):
      ...   print(x + y)
      ...
      >>> add
      Actor(<function add at 0x106c6d488>, queue_name='default', actor_name='add')

      >>> add(1, 2)
      3

      >>> add.send(1, 2)
      Message(
        queue_name='default',
        actor_name='add',
        args=(1, 2), kwargs={}, options={},
        message_id='e0d27b45-7900-41da-bb97-553b8a081206',
        message_timestamp=1497862448685)

    Parameters:
      fn(callable): The function to wrap.
      actor_name(str): The name of the actor.
      queue_name(str): The name of the queue to use.
      priority(int): The actor's global priority.  If two tasks have
        been pulled on a worker concurrently and one has a higher
        priority than the other then it will be processed first.
        Lower numbers represent higher priorities.
      broker(Broker): The broker to use with this actor.
      \**options(dict): Arbitrary options that vary with the set of
        middleware that you use.  See ``get_broker().actor_options``.

    Returns:
      Actor
    """
    def decorator(fn):
        nonlocal actor_name, broker
        actor_name = actor_name or fn.__name__
        if not _queue_name_re.fullmatch(queue_name):
            raise ValueError(
                "Queue names must start with a letter or an underscore followed "
                "by any number of letters, digits, dashes or underscores."
            )

        broker = broker or get_broker()
        invalid_options = set(options) - broker.actor_options
        if invalid_options:
            raise ValueError(
                f"The following actor options are undefined: {', '.join(invalid_options)}. "
                "Did you forget to add a middleware to your Broker?"
            )

        return Actor(
            fn, actor_name=actor_name, queue_name=queue_name,
            priority=priority, broker=broker, options=options,
        )

    if fn is None:
        return decorator
    return decorator(fn)


class Actor:
    """Thin wrapper around callables that stores metadata about how
    they should be executed asynchronously.
    """

    def __init__(self, fn, *, broker, actor_name, queue_name, priority, options):
        self.fn = fn
        self.broker = broker
        self.actor_name = actor_name
        self.queue_name = queue_name
        self.priority = priority
        self.options = options
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
        return self.send_with_options(args=args, kwargs=kwargs)

    def send_with_options(self, *, args=None, kwargs=None, delay=None, **options):
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
            args=args or (), kwargs=kwargs or {},
            options=options,
        )

        self.broker.enqueue(message, delay=delay)
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
