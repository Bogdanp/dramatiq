# This file is a part of Dramatiq.
#
# Copyright (C) 2017,2018,2024 CLEARTYPE SRL <bogdan@cleartype.io>
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
    Callable,
    Dict,
    List,
    Optional,
    Union,
)

if TYPE_CHECKING:
    from .actor import Actor
    from .broker import Broker

_global_registry: Optional[Registry] = None


def get_registry() -> Optional[Registry]:
    """Get the current global task registry, if registry mode is enabled."""
    return _global_registry


def set_registry(registry: Optional[Registry]) -> None:
    """Set the current global task registry."""
    global _global_registry
    _global_registry = registry


def enable_registry() -> Registry:
    """Enable global task registry mode.

    When registry mode is enabled, actors declared with the standard `@dramatiq.actor`
    decorator will automatically be placed into this global registry rather than
    triggering an implicit broker creation or requiring a global broker.
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = Registry()
    return _global_registry


def disable_registry() -> None:
    """Disable global task registry mode and reset the global registry."""
    global _global_registry
    _global_registry = None


class Registry:
    """A task registry that abstracts actor definitions from broker instances.

    Actors can be declared using `@registry.actor(...)` without requiring an
    active Broker or triggering an implicit broker initialization.
    Later, the registry can be bound to one or more brokers via `registry.bind(broker)`.
    """

    def __init__(self) -> None:
        self.actors: Dict[str, Actor] = {}

    def declare_actor(self, actor: Actor) -> None:
        """Add an actor to this registry.

        Parameters:
          actor(Actor): The actor to declare.

        Raises:
          ValueError: If an actor with the same name is already registered.
        """
        if actor.actor_name in self.actors:
            raise ValueError(f"An actor named {actor.actor_name!r} is already registered in this registry.")
        self.actors[actor.actor_name] = actor

    def actor(
        self,
        fn: Optional[Callable] = None,
        *,
        actor_class: Optional[Callable[..., Actor]] = None,
        actor_name: Optional[str] = None,
        queue_name: str = "default",
        priority: int = 0,
        **options: Any,
    ) -> Any:
        """Decorator to declare an actor in this registry without an immediate broker.

        Parameters:
          fn(callable): The function to wrap.
          actor_class(callable): The actor class to use.
          actor_name(str): The actor's name.
          queue_name(str): The queue name.
          priority(int): The actor's priority.
          options: Arbitrary options for middleware and broker.
        """
        from .actor import Actor as DefaultActor

        actual_class = actor_class or DefaultActor

        def decorator(func: Callable) -> Actor:
            name = actor_name or func.__name__
            created_actor = actual_class(
                func,
                actor_name=name,
                queue_name=queue_name,
                priority=priority,
                broker=None,
                options=options,
            )
            self.declare_actor(created_actor)
            return created_actor

        if fn is None:
            return decorator
        return decorator(fn)

    def bind(self, broker: Broker) -> None:
        """Bind all registered actors in this registry to a broker.

        Parameters:
          broker(Broker): The broker instance to bind actors to.
        """
        for actor in self.actors.values():
            actor.broker = broker
            broker.declare_actor(actor)

    def transfer_actors(self, broker: Broker) -> None:
        """Alias for `bind(broker)`."""
        self.bind(broker)

    def __contains__(self, actor_name: str) -> bool:
        return actor_name in self.actors

    def __getitem__(self, actor_name: str) -> Actor:
        return self.actors[actor_name]

    def __iter__(self):
        return iter(self.actors.values())

    def __len__(self) -> int:
        return len(self.actors)


def transfer_actors(broker: Broker, registries: Union[List[Registry], Registry]) -> None:
    """Transfer actors from one or more registries to a broker.

    Parameters:
      broker(Broker): The target broker.
      registries(list[Registry] | Registry): The registry or list of registries.
    """
    if isinstance(registries, Registry):
        registries = [registries]
    for reg in registries:
        reg.bind(broker)
