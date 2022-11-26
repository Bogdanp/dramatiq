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

import hashlib
import time
import typing

from ..common import compute_backoff, q_name
from ..encoder import Encoder
from .errors import ResultMissing, ResultTimeout
from .result import unwrap_result, wrap_exception, wrap_result

#: The default timeout for blocking get operations in milliseconds.
DEFAULT_TIMEOUT = 10000

#: The minimum amount of time in ms to wait between polls.
BACKOFF_FACTOR = 100

#: Canary value that is returned when a result hasn't been set yet.
Missing = type("Missing", (object,), {})()

#: A type alias representing backend results.
Result = typing.Any

#: A union representing a Result that may or may not be there.
MResult = typing.Union[typing.Type[object], Result]


class ResultBackend:
    """ABC for result backends.

    Parameters:
      namespace(str): The logical namespace under which the data
        should be stored.
      encoder(Encoder): The encoder to use when storing and retrieving
        result data.  Defaults to :class:`.JSONEncoder`.
    """

    def __init__(self, *, namespace: str = "dramatiq-results", encoder: typing.Optional[Encoder] = None):
        from ..message import get_encoder

        self.namespace = namespace
        self.encoder = encoder or get_encoder()

    def unwrap_result(self, res):
        """Unwrap the serialized result.  Passes through to
        :func:`unwrap_result` by default, but can be overridden to
        complement changes to how :meth:`store_result` or
        :meth:`store_exception` serialize their results.

        Parameters:
          res(object): The result data, typically a dict.

        Returns:
          object: The result.
        """
        return unwrap_result(res)

    def get_result(self, message, *, block: bool = False, timeout: typing.Optional[int] = None) -> Result:
        """Get a result from the backend.

        Parameters:
          message(Message)
          block(bool): Whether or not to block until a result is set.
          timeout(int): The maximum amount of time, in ms, to wait for
            a result when block is True.  Defaults to 10 seconds.

        Raises:
          ResultMissing: When block is False and the result isn't set.
          ResultTimeout: When waiting for a result times out.

        Returns:
          object: The result.
        """
        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        end_time = time.monotonic() + timeout / 1000
        message_key = self.build_message_key(message)

        attempts = 0
        while True:
            result = self._get(message_key)
            if result is Missing and block:
                attempts, delay = compute_backoff(attempts, factor=BACKOFF_FACTOR)
                delay /= 1000
                if time.monotonic() + delay > end_time:
                    raise ResultTimeout(message)

                time.sleep(delay)
                continue

            elif result is Missing:
                raise ResultMissing(message)

            else:
                return self.unwrap_result(result)

    def store_result(self, message, result: Result, ttl: int) -> None:
        """Store a result in the backend.

        Parameters:
          message(Message)
          result(object): Must be serializable.
          ttl(int): The maximum amount of time the result may be
            stored in the backend for.
        """
        message_key = self.build_message_key(message)
        return self._store(message_key, wrap_result(result), ttl)

    def store_exception(self, message, exception: Exception, ttl: int) -> None:
        """Store an exception in the backend.

        Parameters:
          message(Message)
          exception(Exception)
          ttl(int): The maximum amount of time the exception may be
            stored in the backend for.
        """
        message_key = self.build_message_key(message)
        return self._store(message_key, wrap_exception(exception), ttl)

    def build_message_key(self, message) -> str:
        """Given a message, return its globally-unique key.

        Parameters:
          message(Message)

        Returns:
          str
        """
        message_key = "%(namespace)s:%(queue_name)s:%(actor_name)s:%(message_id)s" % {
            "namespace": self.namespace,
            "queue_name": q_name(message.queue_name),
            "actor_name": message.actor_name,
            "message_id": message.message_id,
        }
        return hashlib.md5(message_key.encode("utf-8")).hexdigest()

    def _get(self, message_key: str) -> MResult:  # pragma: no cover
        """Get a result from the backend.  Subclasses may implement
        this method if they want to use the default, polling,
        implementation of get_result.
        """
        raise NotImplementedError("%(classname)r does not implement _get()" % {
            "classname": type(self).__name__,
        })

    def _store(self, message_key: str, result: Result, ttl: int) -> None:  # pragma: no cover
        """Store a result in the backend.  Subclasses may implement
        this method if they want to use the default implementation of
        set_result.
        """
        raise NotImplementedError("%(classname)r does not implement _store()" % {
            "classname": type(self).__name__,
        })
