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

import dataclasses
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar

from .broker import get_broker
from .composition import pipeline
from .encoder import Encoder, JSONEncoder
from .errors import DecodeError
from .results import ResultBackend

#: The global encoder instance.
global_encoder: Encoder = JSONEncoder()

R = TypeVar("R", covariant=True)


def get_encoder() -> Encoder:
    """Get the global encoder object.

    Returns:
      Encoder
    """
    return global_encoder


def set_encoder(encoder: Encoder) -> None:
    """Set the global encoder object.

    Parameters:
      encoder(Encoder): The encoder instance to use when serializing
        messages.
    """
    global global_encoder
    global_encoder = encoder


def generate_unique_id() -> str:
    """Generate a globally-unique message id."""
    return str(uuid.uuid4())


@dataclasses.dataclass(frozen=True)
class Message(Generic[R]):
    """Encapsulates metadata about messages being sent to individual actors.

    Parameters:
      queue_name(str): The name of the queue the message belongs to.
      actor_name(str): The name of the actor that will receive the message.
      args(tuple): Positional arguments that are passed to the actor.
      kwargs(dict): Keyword arguments that are passed to the actor.
      options(dict): Arbitrary options passed to the broker and middleware.
      message_id(str): A globally-unique id assigned to the actor.
      message_timestamp(int): The UNIX timestamp in milliseconds
        representing when the message was first enqueued.
    """

    queue_name: str
    actor_name: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    options: dict[str, Any]
    message_id: str = dataclasses.field(default_factory=generate_unique_id)
    message_timestamp: int = dataclasses.field(default_factory=lambda: int(time.time() * 1000))

    def __post_init__(self):
        # For backwards-compatibility, enforce that `args' is a tuple.
        if type(self.args) is not tuple:
            # The class is marked frozen, so we have to use the
            # primitive setattr here.  Direct assignment would fail.
            object.__setattr__(self, "args", tuple(self.args))

    def __or__(self, other) -> pipeline:
        """Combine this message into a pipeline with "other"."""
        return pipeline([self, other])

    def asdict(self) -> dict[str, Any]:
        """Convert this message to a dictionary."""
        # For backward compatibility, we can't use `dataclasses.asdict`
        # because it creates a copy of all values, including `options`.
        result = {}
        for field in dataclasses.fields(self):
            result[field.name] = getattr(self, field.name)
        return result

    @classmethod
    def decode(cls, data: bytes) -> Message:
        """Convert a bytestring to a message.

        Raises:
          DecodeError: When the decoder raises an exception while
            decoding `data`.
        """
        try:
            fields = global_encoder.decode(data)
            fields["args"] = tuple(fields["args"])
            return cls(**fields)
        except Exception as e:
            raise DecodeError("Failed to decode message.", data, e) from e

    def encode(self) -> bytes:
        """Convert this message to a bytestring."""
        return global_encoder.encode(self.asdict())

    def copy(self, **attributes) -> Message:
        """Create a copy of this message."""
        new_options = attributes.pop("options", {})
        return dataclasses.replace(self, **attributes, options={**self.options, **new_options})

    def get_result(
        self,
        *,
        backend: Optional[ResultBackend] = None,
        block: bool = False,
        timeout: Optional[int] = None,
    ) -> R:
        """Get the result associated with this message from a result
        backend.

        Warning:
          If you use multiple result backends or brokers you should
          always pass the backend parameter.  This method is only able
          to infer the result backend off of the default broker.

        Parameters:
          backend(ResultBackend): The result backend to use to get the
            result.  If omitted, this method will try to find and use
            the result backend on the default broker instance.
          block(bool): Whether or not to block while waiting for a
            result.
          timeout(int): The maximum amount of time, in ms, to block
            while waiting for a result.  Defaults to 10 seconds.

        Raises:
          RuntimeError: If there is no result backend on the default
            broker.
          ResultMissing: When block is False and the result isn't set.
          ResultTimeout: When waiting for a result times out.

        Returns:
          object: The result.
        """
        if backend is None:
            broker = get_broker()
            backend = broker.get_results_backend()

        return backend.get_result(self, block=block, timeout=timeout)

    def __str__(self) -> str:
        params = ", ".join(repr(arg) for arg in self.args)
        if self.kwargs:
            params += ", " if params else ""
            params += ", ".join("%s=%r" % (name, value) for name, value in self.kwargs.items())

        return "%s(%s)" % (self.actor_name, params)

    def __lt__(self, other: Message) -> bool:
        return dataclasses.astuple(self) < dataclasses.astuple(other)

    # Backwards-compatibility with namedtuple.
    _asdict = asdict

    @property
    def _field_defaults(self) -> dict[str, Any]:
        return {f.name: f.default for f in dataclasses.fields(self) if f.default is not dataclasses.MISSING}

    @property
    def _fields(self) -> tuple[str, ...]:
        return tuple(f.name for f in dataclasses.fields(self))

    def _replace(self, **changes) -> Message[R]:
        return dataclasses.replace(self, **changes)

    @property
    def message_datetime(self) -> datetime:
        """Read ``message_timestamp`` as a UTC-aware datetime.

        Datetime precision is limited by the representation of ``Message.message_timestamp``, which is an
        integer storing milliseconds.
        """
        unix_seconds, ms = divmod(self.message_timestamp, 1000)
        return datetime.fromtimestamp(unix_seconds, tz=timezone.utc).replace(microsecond=ms * 1000)
