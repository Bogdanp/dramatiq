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

import dataclasses
import time
import uuid
from typing import Any, Dict, Generic, Optional, TypeVar

from .broker import get_broker
from .composition import pipeline
from .encoder import Encoder, JSONEncoder
from .errors import DecodeError
from .results import ResultBackend, Results

#: The global encoder instance.
global_encoder: Encoder = JSONEncoder()

R = TypeVar("R")


def get_encoder() -> Encoder:
    """Get the global encoder object.

    Returns:
      Encoder
    """
    global global_encoder
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
    """Generate a globally-unique message id.
    """
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
    args: tuple
    kwargs: Dict[str, Any]
    options: Dict[str, Any]
    message_id: str = dataclasses.field(default_factory=generate_unique_id)
    message_timestamp: int = dataclasses.field(default_factory=lambda: int(time.time() * 1000))

    def __or__(self, other) -> pipeline:
        """Combine this message into a pipeline with "other".
        """
        return pipeline([self, other])

    def asdict(self) -> Dict[str, Any]:
        """Convert this message to a dictionary.
        """
        return dataclasses.asdict(self)

    @classmethod
    def decode(cls, data: bytes) -> "Message":
        """Convert a bytestring to a message.

        Raises:
          DecodeError: When the decoder raises an exception while
            decoding `data`.
        """
        try:
            return cls(**global_encoder.decode(data))
        except Exception as e:
            raise DecodeError("Failed to decode message.", data, e) from e

    def encode(self) -> bytes:
        """Convert this message to a bytestring.
        """
        return global_encoder.encode(self.asdict())

    def copy(self, **attributes) -> "Message":
        """Create a copy of this message.
        """
        new_options = attributes.pop("options", {})
        return dataclasses.replace(self, **attributes, options={**self.options, **new_options})

    def get_result(
        self, *,
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
            while waiting for a result.

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
            for middleware in broker.middleware:
                if isinstance(middleware, Results):
                    backend = middleware.backend
                    break
            else:
                raise RuntimeError("The default broker doesn't have a results backend.")

        return backend.get_result(self, block=block, timeout=timeout)

    def __str__(self) -> str:
        params = ", ".join(repr(arg) for arg in self.args)
        if self.kwargs:
            params += ", " if params else ""
            params += ", ".join("%s=%r" % (name, value) for name, value in self.kwargs.items())

        return "%s(%s)" % (self.actor_name, params)
