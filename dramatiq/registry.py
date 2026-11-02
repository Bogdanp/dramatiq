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

from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Optional,
    ParamSpec,
    TypeVar,
    Union,
    overload,
)

from .errors import ActorNotFound

if TYPE_CHECKING:
    from .actor import Actor, ActorDecorator
    from .broker import Broker
    from .message import Message

P = ParamSpec("P")
R = TypeVar("R")

#: The global actor registry instance when registry mode is enabled.
global_registry: Optional[Registry] = None


def get_registry() -> Optional[Registry]:
    """Get the active global :class:`Registry` instance, if registry
    mode has been enabled via :func:`enable_registry`.

    Returns:
      Optional[Registry]: The active global registry or ``None``.
    """
    return global_registry


def set_registry(registry: Optional[Registry]) -> None:
    """Configure the global :class:`Registry` instance.

    Parameters:
      registry(Optional[Registry]): The registry instance to use, or
        ``None`` to disable global registry mode.
    """
    global global_registry
    global_registry = registry


def enable_registry(registry: Optional[Registry] = None) -> Registry:
    """Enable global registry mode so actors can be declared via
    :func:`dramatiq.actor` before a :class:`~dramatiq.Broker` is
    instantiated.

    Parameters:
      registry(Optional[Registry]): An optional existing registry to
        activate. If omitted, a new :class:`Registry` is created.

    Returns:
      Registry: The active global registry.
    """
    if registry is None:
        registry = Registry()
    set_registry(registry)
    return registry


def disable_registry() -> None:
    """Disable global registry mode."""
    set_registry(None)


class Registry:
    """An actor registry that allows declaring actors independently of a
    :class:`~dramatiq.Broker` instance and binding them to a broker later.

    Attributes:
      actors(dict[str, Actor]): The actors declared in this registry.
      broker(Optional[Broker]): The broker bound to this registry, if any.
    """

    def __init__(self, *, broker: Optional[Broker] = None) -> None:
        self.actors: dict[str, Actor[Any, Any]] = {}
        self.broker: Optional[Broker] = broker

    @property
    def actor_options(self) -> set[str]:
        if self.broker is not None:
            return self.broker.actor_options
        return set()

    def declare_actor(self, actor: Actor[Any, Any]) -> None:
        """Register an actor with this registry. If a broker is already
        bound to this registry, the actor is also validated and declared
        on that broker immediately.

        Parameters:
          actor(Actor): The actor being declared.
        """
        if actor.actor_name in self.actors and self.actors[actor.actor_name] is not actor:
            raise ValueError(f"An actor named {actor.actor_name!r} is already registered.")

        if self.broker is not None:
            self._validate_actor_for_broker(actor, self.broker)
            self.actors[actor.actor_name] = actor
            actor.broker = self.broker
            self.broker.declare_actor(actor)
        else:
            self.actors[actor.actor_name] = actor

    def get_actor(self, actor_name: str) -> Actor[Any, Any]:
        """Look up a registered actor by name.

        Parameters:
          actor_name(str): The actor name to look up.

        Raises:
          ActorNotFound: If the actor was never registered.

        Returns:
          Actor: The actor instance.
        """
        try:
            return self.actors[actor_name]
        except KeyError:
            raise ActorNotFound(actor_name) from None

    def get_declared_actors(self) -> set[str]:
        """Get the names of all actors declared in this registry.

        Returns:
          set[str]: Registered actor names.
        """
        return set(self.actors.keys())

    @staticmethod
    def _validate_actor_for_broker(actor: Actor[Any, Any], broker: Broker) -> None:
        if actor.actor_name in broker.actors and broker.actors[actor.actor_name] is not actor:
            raise ValueError(f"An actor named {actor.actor_name!r} is already registered.")

        invalid_options = set(actor.options) - broker.actor_options
        if invalid_options:
            invalid_options_list = ", ".join(invalid_options)
            raise ValueError(
                "The following actor options are undefined: %s. Did you forget to add a middleware to your Broker?"
                % invalid_options_list
            )

    def bind_broker(self, broker: Optional[Broker] = None) -> Broker:
        """Bind all actors in this registry to ``broker`` (or the global
        broker if omitted) and declare them on it.

        Parameters:
          broker(Optional[Broker]): Target broker instance.

        Returns:
          Broker: The bound broker.
        """
        from .broker import get_broker

        target_broker = broker or get_broker()
        for registered_actor in self.actors.values():
            self._validate_actor_for_broker(registered_actor, target_broker)

        self.broker = target_broker
        for registered_actor in self.actors.values():
            registered_actor.broker = target_broker
            target_broker.declare_actor(registered_actor)

        return target_broker

    def transfer_actors(self, broker: Optional[Broker] = None) -> Broker:
        """Alias for :meth:`bind_broker`."""
        return self.bind_broker(broker)

    def enqueue(self, message: Message[Any], *, delay: Optional[int] = None) -> Message[Any]:
        """Enqueue a message via the bound broker, or raise a
        :class:`RuntimeError` if no broker has been bound yet.
        """
        if self.broker is None:
            raise RuntimeError(
                "Actor registry is not bound to a broker. "
                "Call registry.bind_broker(broker) or dramatiq.set_broker(broker) before sending messages."
            )
        return self.broker.enqueue(message, delay=delay)

    @overload
    def actor(self, fn: Callable[P, Awaitable[R]]) -> Actor[P, R]: ...

    @overload
    def actor(self, fn: Callable[P, R]) -> Actor[P, R]: ...

    @overload
    def actor(
        self,
        *,
        queue_name: str = "default",
        priority: int = 0,
        actor_name: Optional[str] = None,
        actor_class: Optional[Callable[..., Actor[Any, Any]]] = None,
        **options: Any,
    ) -> ActorDecorator: ...

    def actor(
        self,
        fn: Optional[Callable[P, Union[Awaitable[R], R]]] = None,
        *,
        actor_class: Optional[Callable[..., Actor[P, R]]] = None,
        actor_name: Optional[str] = None,
        queue_name: str = "default",
        priority: int = 0,
        **options: Any,
    ) -> Union[Actor[P, R], Callable[..., Actor[P, R]]]:
        """Declare an actor in this registry."""
        from .actor import Actor as DefaultActor
        from .actor import _queue_name_re

        resolved_actor_class: Callable[..., Actor[P, R]] = actor_class or DefaultActor

        def decorator(target_fn: Callable[..., Union[Awaitable[R], R]]) -> Actor[P, R]:
            resolved_name = actor_name or target_fn.__name__
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
                        "The following actor options are undefined: %s. "
                        "Did you forget to add a middleware to your Broker?" % invalid_options_list
                    )

            return resolved_actor_class(
                target_fn,
                actor_name=resolved_name,
                queue_name=queue_name,
                priority=priority,
                broker=self,
                options=options,
            )

        if fn is None:
            return decorator
        return decorator(fn)

    def __getattr__(self, name: str) -> Any:
        if self.broker is not None:
            return getattr(self.broker, name)
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")
