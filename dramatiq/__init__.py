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

import warnings

from .actor import Actor, actor
from .broker import Broker, Consumer, MessageProxy, get_broker, set_broker
from .composition import group, pipeline
from .encoder import Encoder, JSONEncoder, PickleEncoder
from .errors import (
    ActorNotFound,
    BrokerConnectionError,
    BrokerError,
    ConnectionClosed,
    ConnectionFailed,
    DecodeError,
    DramatiqError,
    QueueJoinTimeout,
    QueueNotFound,
    RateLimitExceeded,
    Retry,
)
from .generic import GenericActor
from .logging import get_logger
from .message import Message, get_encoder, set_encoder
from .middleware import Middleware
from .worker import ConsumerThread, Worker, WorkerThread

__all__ = [
    # Actors
    "Actor",
    "GenericActor",
    "actor",
    # Brokers
    "Broker",
    "Consumer",
    "MessageProxy",
    "get_broker",
    "set_broker",
    # Composition
    "group",
    "pipeline",
    # Encoding
    "Encoder",
    "JSONEncoder",
    "PickleEncoder",
    # Errors
    "DramatiqError",
    "BrokerError",
    "DecodeError",
    "ActorNotFound",
    "QueueNotFound",
    "QueueJoinTimeout",
    "BrokerConnectionError",
    "ConnectionClosed",
    "ConnectionFailed",
    "RateLimitExceeded",
    "Retry",
    # Logging
    "get_logger",
    # Messages
    "Message",
    "get_encoder",
    "set_encoder",
    # Middlware
    "Middleware",
    # Workers
    "Worker",
    "ConsumerThread",
    "WorkerThread",
]

__version__ = "2.0.1"


def __getattr__(name):
    if name == "ConnectionError":
        warnings.warn(
            "The class 'ConnectionError' has been renamed to 'BrokerConnectionError'. "
            "The old name 'ConnectionError' will be removed in dramatiq v3.0.0.",
            category=DeprecationWarning,
            stacklevel=2,
        )
        return BrokerConnectionError

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
