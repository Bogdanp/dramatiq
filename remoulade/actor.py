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

import re

from .logging import get_logger
from .message import Message

#: The regular expression that represents valid queue names.
_queue_name_re = re.compile(r"[a-zA-Z_][a-zA-Z0-9._-]*")


def actor(fn=None, *, actor_name=None, queue_name="default", priority=0, **options):
    """Declare an actor.

    Examples:

      >>> import remoulade

      >>> @remoulade.actor
      ... def add(x, y):
      ...   print(x + y)
      ...
      >>> add
      Actor(<function add at 0x106c6d488>, queue_name='default', actor_name='add')

      You need to declare an actor before using it
      >>> get_broker().declare_actor(add)
      None

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
      **options(dict): Arbitrary options that vary with the set of
        middleware that you use.  See ``get_broker().actor_options``.

    Returns:
      Actor: The decorated function.
    """
    def decorator(fn):
        nonlocal actor_name
        actor_name = actor_name or fn.__name__
        if not _queue_name_re.fullmatch(queue_name):
            raise ValueError(
                "Queue names must start with a letter or an underscore followed "
                "by any number of letters, digits, dashes or underscores."
            )

        return Actor(fn, actor_name=actor_name, queue_name=queue_name, priority=priority, options=options)

    if fn is None:
        return decorator
    return decorator(fn)


class Actor:
    """Thin wrapper around callables that stores metadata about how
    they should be executed asynchronously.  Actors are callable.

    Attributes:
      logger(Logger): The actor's logger.
      fn(callable): The underlying callable.
      broker(Broker): The broker this actor is bound to.
      actor_name(str): The actor's name.
      queue_name(str): The actor's queue.
      priority(int): The actor's priority.
      options(dict): Arbitrary options that are passed to the broker
        and middleware.
    """

    def __init__(self, fn, *, actor_name, queue_name, priority, options):
        self.logger = get_logger(fn.__module__, actor_name)
        self.fn = fn
        self.broker = None
        self.actor_name = actor_name
        self.queue_name = queue_name
        self.priority = priority
        self.options = options

    def set_broker(self, broker):
        invalid_options = set(self.options) - broker.actor_options
        if invalid_options:
            invalid_options_list = ", ".join(invalid_options)
            message = "The following actor options are undefined: %s. " % invalid_options_list
            message += "Did you forget to add a middleware to your Broker?"
            raise ValueError(message)
        self.broker = broker

    def message(self, *args, **kwargs):
        """Build a message.  This method is useful if you want to
        compose actors.  See the actor composition documentation for
        details.

        Parameters:
          *args(tuple): Positional arguments to send to the actor.
          **kwargs(dict): Keyword arguments to send to the actor.

        Examples:
          >>> (add.message(1, 2) | add.message(3))
          pipeline([add(1, 2), add(3)])

        Returns:
          Message: A message that can be enqueued on a broker.
        """
        return self.message_with_options(args=args, kwargs=kwargs)

    def message_with_options(self, *, args=None, kwargs=None, **options):
        """Build a message with an arbitray set of processing options.
        This method is useful if you want to compose actors.  See the
        actor composition documentation for details.

        Parameters:
          args(tuple): Positional arguments that are passed to the actor.
          kwargs(dict): Keyword arguments that are passed to the actor.
          **options(dict): Arbitrary options that are passed to the
            broker and any registered middleware.

        Returns:
          Message: A message that can be enqueued on a broker.
        """
        for name in ["on_failure", "on_success"]:
            callback = options.get(name)
            if isinstance(callback, Actor):
                options[name] = callback.actor_name

            elif not isinstance(callback, (type(None), str)):
                raise TypeError(name + " value must be an Actor")

        return Message(
            queue_name=self.queue_name,
            actor_name=self.actor_name,
            args=args or (), kwargs=kwargs or {},
            options=options,
        )

    def send(self, *args, **kwargs):
        """Asynchronously send a message to this actor.

        Parameters:
          *args(tuple): Positional arguments to send to the actor.
          **kwargs(dict): Keyword arguments to send to the actor.

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
          delay(int): The minimum amount of time, in milliseconds, the
            message should be delayed by.
          **options(dict): Arbitrary options that are passed to the
            broker and any registered middleware.

        Returns:
          Message: The enqueued message.
        """
        if not self.broker:
            raise ValueError("No broker is set, did you forget to call set_broker ?")
        message = self.message_with_options(args=args, kwargs=kwargs, **options)
        return self.broker.enqueue(message, delay=delay)

    def __call__(self, *args, **kwargs):
        """Synchronously call this actor.

        Parameters:
          *args: Positional arguments to send to the actor.
          **kwargs: Keyword arguments to send to the actor.

        Returns:
          Whatever the underlying function backing this actor returns.
        """
        return self.fn(*args, **kwargs)

    def __repr__(self):
        return "Actor(%(fn)r, queue_name=%(queue_name)r, actor_name=%(actor_name)r)" % vars(self)

    def __str__(self):
        return "Actor(%(actor_name)s)" % vars(self)
