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
from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional, ParamSpec, TypeVar, Union, overload

from .actor import Actor, ActorDecorator, _queue_name_re
from .broker import Broker, Consumer, get_broker
from .message import Message

P = ParamSpec("P")
R = TypeVar("R")


class Registry(Broker):
    """Collect actors before binding them to a broker."""

    def __init__(self) -> None:
        super().__init__(middleware=[])

    @overload
    def actor(self, fn: Callable[P, Awaitable[R]]) -> Actor[P, R]:
        pass

    @overload
    def actor(self, fn: Callable[P, R]) -> Actor[P, R]:
        pass

    @overload
    def actor(
        self,
        *,
        queue_name: str = "default",
        priority: int = 0,
        actor_name: Optional[str] = None,
        actor_class: Callable[..., Actor[Any, Any]] = Actor,
        **options: Any,
    ) -> ActorDecorator:
        pass

    def actor(
        self,
        fn: Optional[Callable[P, Union[Awaitable[R], R]]] = None,
        *,
        actor_class: Callable[..., Actor[P, R]] = Actor,
        actor_name: Optional[str] = None,
        queue_name: str = "default",
        priority: int = 0,
        **options: Any,
    ) -> Union[Actor[P, R], Callable]:
        """Declare an actor on this registry."""

        def decorator(fn: Callable[..., Union[Awaitable[R], R]]) -> Actor[P, R]:
            resolved_actor_name = actor_name or fn.__name__
            if not _queue_name_re.fullmatch(queue_name):
                raise ValueError(
                    "Queue names must start with a letter or an underscore followed "
                    "by any number of letters, digits, dashes or underscores."
                )

            return actor_class(
                fn,
                actor_name=resolved_actor_name,
                queue_name=queue_name,
                priority=priority,
                broker=self,
                options=options,
            )

        if fn is None:
            return decorator
        return decorator(fn)

    def bind(self, broker: Optional[Broker] = None) -> Broker:
        """Bind all actors in this registry to a broker."""
        broker = broker or get_broker()
        actors = list(self.actors.values())
        for actor in actors:
            self._validate_actor(actor, broker)

        for actor in actors:
            actor.broker = broker
            broker.declare_actor(actor)

        return broker

    def declare_actor(self, actor: Actor) -> None:
        """Declare a new actor on this registry."""
        self.emit_before("declare_actor", actor)
        self.actors[actor.actor_name] = actor
        self.emit_after("declare_actor", actor)

    def consume(self, queue_name: str, prefetch: int = 1, timeout: int = 30000) -> Consumer:
        raise RuntimeError("Actors declared on a Registry must be bound to a Broker before they can consume messages.")

    def declare_queue(self, queue_name: str) -> None:
        raise RuntimeError("Actors declared on a Registry must be bound to a Broker before queues can be declared.")

    def enqueue(self, message: Message, *, delay: Optional[int] = None) -> Message:
        raise RuntimeError("Actors declared on a Registry must be bound to a Broker before messages can be sent.")

    def flush(self, queue_name: str) -> None:
        raise RuntimeError("Actors declared on a Registry must be bound to a Broker before queues can be flushed.")

    def flush_all(self) -> None:
        raise RuntimeError("Actors declared on a Registry must be bound to a Broker before queues can be flushed.")

    def join(self, queue_name: str, *, timeout: Optional[int] = None) -> None:
        raise RuntimeError("Actors declared on a Registry must be bound to a Broker before queues can be joined.")

    def _validate_actor(self, actor: Actor, broker: Broker) -> None:
        invalid_options = set(actor.options) - broker.actor_options
        if invalid_options:
            invalid_options_list = ", ".join(invalid_options)
            raise ValueError(
                "The following actor options are undefined: %s. Did you forget to add a middleware to your Broker?"
                % invalid_options_list
            )

        registered_actor = broker.actors.get(actor.actor_name)
        if registered_actor is not None and registered_actor is not actor:
            raise ValueError(f"An actor named {actor.actor_name!r} is already registered.")
