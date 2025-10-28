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

import re
import time
from datetime import timedelta
from inspect import iscoroutinefunction
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    Optional,
    ParamSpec,
    TypeVar,
    Union,
    overload,
)

from .asyncio import async_to_sync
from .broker import Broker, get_broker
from .logging import get_logger
from .message import Message

#: The regular expression that represents valid queue names.
_queue_name_re = re.compile(r"[a-zA-Z_][a-zA-Z0-9._-]*")

# Type variables for the Actor function's parameters and return type.
P = ParamSpec("P")
R = TypeVar("R")


class Actor(Generic[P, R]):
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

    def __init__(
        self,
        fn: Callable[P, Union[R, Awaitable[R]]],
        *,
        broker: Broker,
        actor_name: str,
        queue_name: str,
        priority: int,
        options: dict[str, Any],
    ) -> None:
        if actor_name in broker.actors:
            raise ValueError(f"An actor named {actor_name!r} is already registered.")

        self.logger = get_logger(fn.__module__ or "_", actor_name)
        self.fn = async_to_sync(fn) if iscoroutinefunction(fn) else fn
        self.broker = broker
        self.actor_name = actor_name
        self.queue_name = queue_name
        self.priority = priority
        self.options = options
        self.broker.declare_actor(self)

    def message(self, *args: P.args, **kwargs: P.kwargs) -> Message[R]:
        """Build a message.  This method is useful if you want to
        compose actors.  See the actor composition documentation for
        details.

        Parameters:
          *args(tuple): Positional arguments to send to the actor.
          **kwargs: Keyword arguments to send to the actor.

        Examples:
          >>> (add.message(1, 2) | add.message(3))
          pipeline([add(1, 2), add(3)])

        Returns:
          Message: A message that can be enqueued on a broker.
        """
        return self.message_with_options(args=args, kwargs=kwargs)

    def message_with_options(
        self,
        *,
        args: tuple = (),
        kwargs: Optional[dict[str, Any]] = None,
        **options,
    ) -> Message[R]:
        """Build a message with an arbitrary set of processing options.
        This method is useful if you want to compose actors.  See the
        actor composition documentation for details.

        Parameters:
          args(tuple): Positional arguments that are passed to the actor.
          kwargs(dict): Keyword arguments that are passed to the actor.
          **options: Arbitrary options that are passed to the
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
            args=args,
            kwargs=kwargs or {},
            options=options,
        )

    def send(self, *args: P.args, **kwargs: P.kwargs) -> Message[R]:
        """Asynchronously send a message to this actor.

        Parameters:
          *args: Positional arguments to send to the actor.
          **kwargs: Keyword arguments to send to the actor.

        Returns:
          Message: The enqueued message.
        """
        return self.send_with_options(args=args, kwargs=kwargs)

    def send_with_options(
        self,
        *,
        args: tuple = (),
        kwargs: Optional[dict[str, Any]] = None,
        delay: Optional[timedelta | int] = None,
        **options,
    ) -> Message[R]:
        """Asynchronously send a message to this actor, along with an
        arbitrary set of processing options for the broker and
        middleware.

        Parameters:
          args(tuple): Positional arguments that are passed to the actor.
          kwargs(dict): Keyword arguments that are passed to the actor.
          delay(int): The minimum amount of time, in milliseconds, the
            message should be delayed by. Also accepts a timedelta.
          **options: Arbitrary options that are passed to the
            broker and any registered middleware.

        Returns:
          Message: The enqueued message.
        """
        if isinstance(delay, timedelta):
            delay = int(delay.total_seconds() * 1000)

        message = self.message_with_options(args=args, kwargs=kwargs, **options)
        return self.broker.enqueue(message, delay=delay)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Any | R | Awaitable[R]:
        """Synchronously call this actor.

        Parameters:
          *args: Positional arguments to send to the actor.
          **kwargs: Keyword arguments to send to the actor.

        Returns:
          Whatever the underlying function backing this actor returns.
        """
        try:
            self.logger.debug("Received args=%r kwargs=%r.", args, kwargs)
            start = time.perf_counter()
            return self.fn(*args, **kwargs)
        finally:
            delta = time.perf_counter() - start
            self.logger.debug("Completed after %.02fms.", delta * 1000)

    def __repr__(self) -> str:
        return "Actor(%(fn)r, queue_name=%(queue_name)r, actor_name=%(actor_name)r)" % vars(self)

    def __str__(self) -> str:
        return "Actor(%(actor_name)s)" % vars(self)


@overload
def actor(fn: Callable[P, Union[Awaitable[R], R]], **kwargs) -> Actor[P, R]:
    pass


@overload
def actor(fn: None = None, **kwargs) -> Callable[[Callable[P, Union[Awaitable[R], R]]], Actor[P, R]]:
    pass


def actor(
    fn: Optional[Callable[P, Union[Awaitable[R], R]]] = None,
    *,
    actor_class: Callable[..., Actor[P, R]] = Actor,
    actor_name: Optional[str] = None,
    queue_name: str = "default",
    priority: int = 0,
    broker: Optional[Broker] = None,
    **options,
) -> Union[Actor[P, R], Callable]:
    """Declare an actor.

    Examples:

      >>> import dramatiq

      >>> @dramatiq.actor
      ... def add(x, y):
      ...     print(x + y)
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
      actor_class(type): Type created by the decorator.  Defaults to
        :class:`Actor` but can be any callable as long as it returns an
        actor and takes the same arguments as the :class:`Actor` class.
      actor_name(str): The name of the actor.
      queue_name(str): The name of the queue to use.
      priority(int): The actor's global priority.  If two tasks have
        been pulled on a worker concurrently and one has a higher
        priority than the other then it will be processed first.
        Lower numbers represent higher priorities.
      broker(Broker): The broker to use with this actor.
      **options: Arbitrary options that vary with the set of
        middleware that you use.  See ``get_broker().actor_options``.

    Returns:
      Actor: The decorated function.
    """

    def decorator(fn: Callable[..., Union[Awaitable[R], R]]) -> Actor[P, R]:
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
            invalid_options_list = ", ".join(invalid_options)
            raise ValueError(
                "The following actor options are undefined: %s. Did you forget to add a middleware to your Broker?"
                % invalid_options_list
            )

        return actor_class(
            fn,
            actor_name=actor_name,
            queue_name=queue_name,
            priority=priority,
            broker=broker,
            options=options,
        )

    if fn is None:
        return decorator
    return decorator(fn)
