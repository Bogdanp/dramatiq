from typing import Callable, Generic, TypeVar, overload

from .broker import Broker
from .message import Message

_CallableType = TypeVar("_CallableType", bound=Callable)


@overload
def actor(  # type: ignore
    fn: None = ...,
    *,
    actor_class: "Actor" = ...,
    actor_name: str = ...,
    queue_name: str = ...,
    priority: int = ...,
    broker: Broker = ...,
    **options
) -> Callable[[_CallableType], Actor[_CallableType]]: ...


@overload
def actor(
    fn: _CallableType = ...,
    *,
    actor_class: "Actor" = ...,
    actor_name: str = ...,
    queue_name: str = ...,
    priority: int = ...,
    broker: Broker = ...,
    **options
) -> Actor[_CallableType]: ...


class Actor(Generic[_CallableType]):
    fn: _CallableType
    broker: Broker
    actor_name: str
    queue_name: str
    priority: int
    options: dict

    def __init__(
        self,
        fn: _CallableType,
        *,
        broker: Broker,
        actor_name: str,
        queue_name: str,
        priority: int,
        options: dict,
    ) -> None: ...

    def message_with_options(self, *, args: tuple = ..., kwargs: dict = ..., **options) -> Message: ...
    def send(self, *args, **kwargs) -> Message: ...
    def send_with_options(self, *, args: tuple = ..., kwargs: dict = ..., delay: int = ..., **options) -> Message: ...

    # TODO: mypy plugin for `send` and `send_with_options`?
    __call__: _CallableType
