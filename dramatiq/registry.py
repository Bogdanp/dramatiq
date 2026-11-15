# This file is a part of Dramatiq.
#
# Copyright (C) 2017-2026 CLEARTYPE SRL <bogdan@cleartype.io>
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

from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Optional,
    ParamSpec,
    TypeVar,
    Union,
)

from .actor import Actor, _queue_name_re
from .errors import ActorNotFound

if TYPE_CHECKING:
    from .broker import Broker
    from .message import Message

P = ParamSpec("P")
R = TypeVar("R")


class Registry:
    """A Registry allows defining a collection of Actors not directly bound to a Broker.

    This allows applications to declare actors before configuring a Broker,
    or to partition actors across distinct queues/workers.
    """

    def __init__(self) -> None:
        self.actors: dict[str, Actor] = {}
        self.broker: Optional[Broker] = None

    @property
    def actor_options(self) -> set[str]:
        if self.broker is not None:
            return self.broker.actor_options
        return set()

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
        """Declare an actor registered with this registry."""

        def decorator(fn: Callable[..., Union[Awaitable[R], R]]) -> Actor[P, R]:
            nonlocal actor_name
            actor_name = actor_name or fn.__name__
            if not _queue_name_re.fullmatch(queue_name):
                raise ValueError(
                    "Queue names must start with a letter or an underscore followed "
                    "by any number of letters, digits, dashes or underscores."
                )

            if self.broker is not None:
                invalid_options = set(options) - self.broker.actor_options
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
                broker=self,  # type: ignore[arg-type]
                options=options,
            )

        if fn is None:
            return decorator
        return decorator(fn)

    def declare_actor(self, actor: Actor) -> None:
        """Register an actor with this registry or forward to broker if bound."""
        if actor.actor_name in self.actors:
            raise ValueError(f"An actor named {actor.actor_name!r} is already registered.")

        self.actors[actor.actor_name] = actor
        if self.broker is not None:
            self.broker.declare_actor(actor)

    def get_actor(self, actor_name: str) -> Actor:
        """Look up an actor by name in this registry."""
        if self.broker is not None:
            return self.broker.get_actor(actor_name)
        try:
            return self.actors[actor_name]
        except KeyError:
            raise ActorNotFound(actor_name) from None

    def get_declared_actors(self) -> set[str]:
        """Get the set of all actor names in this registry."""
        return set(self.actors.keys())

    def bind_broker(self, broker: Broker) -> None:
        """Bind all actors in this registry to a broker.

        Validates that all actor options are supported by the broker's middleware,
        updates actor.broker references, and registers actors with the broker.
        """
        for actor_name, actor in self.actors.items():
            invalid_options = set(actor.options) - broker.actor_options
            if invalid_options:
                invalid_options_list = ", ".join(invalid_options)
                raise ValueError(
                    (
                        "Actor %r specified the following options which are not "
                        "supported by this broker: %s. Did you forget to add a "
                        "middleware to your Broker?"
                    )
                    % (actor_name, invalid_options_list)
                )

            actor.broker = broker
            broker.declare_actor(actor)

        self.broker = broker

    bind = bind_broker

    def enqueue(self, message: Message, *, delay: Optional[int] = None) -> Message:
        """Enqueue a message via the bound broker."""
        if self.broker is None:
            raise RuntimeError(
                f"Cannot enqueue message for actor {message.actor_name!r}: "
                f"registry has not been bound to a broker. Call registry.bind_broker(broker) first."
            )
        return self.broker.enqueue(message, delay=delay)

    def __getattr__(self, name: str) -> Any:
        if self.broker is not None:
            return getattr(self.broker, name)
        raise AttributeError(f"Registry has no attribute {name!r} (broker not bound yet)")


_global_registry: Optional[Registry] = None


def enable_registry(registry: Optional[Registry] = None) -> Registry:
    """Enable registry mode.

    When enabled, actors declared without an explicit broker will register
    with the global registry instead of requiring an immediate Broker instance.
    """
    global _global_registry
    _global_registry = registry or Registry()
    return _global_registry


def get_registry() -> Optional[Registry]:
    """Return the currently active global registry, or None if registry mode is not enabled."""
    return _global_registry


def disable_registry() -> None:
    """Disable registry mode and clear the global registry."""
    global _global_registry
    _global_registry = None
