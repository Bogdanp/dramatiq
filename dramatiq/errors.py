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

from typing import Optional


class DramatiqError(Exception):  # pragma: no cover
    """Base class for all dramatiq errors."""

    def __init__(self, message):  # noqa: B042
        self.message = message

    def __str__(self) -> str:
        return str(self.message) or repr(self.message)


class DecodeError(DramatiqError):
    """Raised when a message fails to decode."""

    def __init__(self, message, data, error):  # noqa: B042
        super().__init__(message)
        self.data = data
        self.error = error


class BrokerError(DramatiqError):
    """Base class for broker-related errors."""


class ActorNotFound(BrokerError):
    """Raised when a message is sent to an actor that hasn't been declared."""


class QueueNotFound(BrokerError):
    """Raised when a message is sent to an queue that hasn't been declared."""


class QueueJoinTimeout(DramatiqError):
    """Raised by brokers that support joining on queues when the join
    operation times out.
    """


class ConnectionError(BrokerError):
    """Base class for broker connection-related errors."""


class ConnectionFailed(ConnectionError):
    """Raised when a broker connection could not be opened."""


class ConnectionClosed(ConnectionError):
    """Raised when a broker connection is suddenly closed."""


class RateLimitExceeded(DramatiqError):
    """Raised when a rate limit has been exceeded."""


class Retry(DramatiqError):
    """Actors may raise this error when they should be retried.  This
    behaves just like any other exception from the perspective of the
    :class:`Retries<dramatiq.middleware.Retries>` middleware, the only
    difference is it doesn't get logged as an error.

    If the ``delay`` argument is provided, then the message will be
    retried after at least that amount of time (in milliseconds).
    """

    def __init__(self, message: str = "", delay: Optional[int] = None):  # noqa: B042
        super().__init__(message)
        self.delay = delay
