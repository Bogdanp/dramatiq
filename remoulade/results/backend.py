# This file is a part of Remoulade.
#
# Copyright (C) 2017,2018 CLEARTYPE SRL <bogdan@cleartype.io>
#
# Remoulade is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# Remoulade is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import time
import typing
from collections import namedtuple

from ..common import compute_backoff
from ..encoder import Encoder
from .errors import ErrorStored, ResultMissing, ResultTimeout

#: The default timeout for blocking get operations in milliseconds.
DEFAULT_TIMEOUT = 10000

#: The minimum amount of time in ms to wait between polls.
BACKOFF_FACTOR = 100

#: Canary value that is returned when a result hasn't been set yet.
Missing = type("Missing", (object,), {})()

#: Canary value that is returned when a result is an error and the error is not raised
FailureResult = type("FailureResult", (object,), {})()


#: A type alias representing backend results.
class BackendResult(namedtuple("BackendResult", ('result', 'error', 'forgot'))):
    def __new__(cls, *, result, error, forgot=False):
        return super().__new__(cls, result, error, forgot)

    def asdict(self):
        return self._asdict()


ForgottenResult = BackendResult(result=None, error=None, forgot=True)

#: A union representing a Result that may or may not be there.
MResult = typing.Union[type(Missing), BackendResult]


class ResultBackend:
    """ABC for result backends.

    Parameters:
      namespace(str): The logical namespace under which the data
        should be stored.
      encoder(Encoder): The encoder to use when storing and retrieving
        result data.  Defaults to :class:`.JSONEncoder`.
    """

    def __init__(self, *, namespace: str = "remoulade-results", encoder: Encoder = None):
        from ..message import get_encoder

        self.namespace = namespace
        self.encoder = encoder or get_encoder()

    def get_result(self, message_id: str, *, block: bool = False, timeout: int = None,  # noqa: F821
                   forget: bool = False, raise_on_error: bool = True) -> BackendResult:
        """Get a result from the backend.

        Parameters:
          message_id(str)
          block(bool): Whether or not to block until a result is set.
          timeout(int): The maximum amount of time, in ms, to wait for
            a result when block is True.  Defaults to 10 seconds.
          forget(bool): Whether or not the result need to be kept.
          raise_on_error(bool): raise an error if the result stored in
            an error

        Raises:
          ResultMissing: When block is False and the result isn't set.
          ResultTimeout: When waiting for a result times out.
          ErrorStored: When the result is an error and raise_on_error is True

        Returns:
          object: The result.
        """
        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        end_time = time.monotonic() + timeout / 1000
        message_key = self.build_message_key(message_id)

        attempts = 0
        while True:
            result = self._get(message_key, forget)
            if result is Missing and block:
                attempts, delay = compute_backoff(attempts, factor=BACKOFF_FACTOR)
                delay /= 1000
                if time.monotonic() + delay > end_time:
                    raise ResultTimeout(message_id)

                time.sleep(delay)
                continue

            elif result is Missing:
                raise ResultMissing(message_id)

            else:
                result = BackendResult(**result)
                return self.process_result(result, raise_on_error)

    @staticmethod
    def process_result(result: BackendResult, raise_on_error: bool):
        """ Raise an error if the result is an error and raise_on_error is true

        Parameters:
          result(Result): the result retrieved from the backend
          raise_on_error(boolean): raise an error if the result stored in an error
        """
        if result.error:
            if raise_on_error:
                raise ErrorStored(result.error)
            return FailureResult
        return result.result

    def increment_group_completion(self, group_id: str) -> int:
        raise NotImplementedError("%(classname)r does not implement increment_group_completion()" % {
            "classname": type(self).__name__,
        })

    def store_result(self, message_id: str, result: BackendResult, ttl: int) -> None:  # noqa: F821
        """Store a result in the backend.

        Parameters:
          message_id(str)
          result(object): Must be serializable.
          ttl(int): The maximum amount of time the result may be
            stored in the backend for.
        """
        message_key = self.build_message_key(message_id)
        return self._store(message_key, result._asdict(), ttl)

    def build_message_key(self, message_id: str) -> str:  # noqa: F821
        """Given a message, return its globally-unique key.

        Parameters:
          message_id(str)

        Returns:
          str
        """
        return "{}:{}".format(self.namespace, message_id)

    def get_status(self, message_ids: typing.List[str]) -> int:
        """ Given a list of messages ids return the number of messages with a result stored"""
        count = 0
        for message_id in message_ids:
            message_key = self.build_message_key(message_id)
            result = self._get(message_key, forget=False)
            if result != Missing:
                count += 1
        return count

    @staticmethod
    def build_group_completion_key(group_id: str) -> str:  # noqa: F821
        return "remoulade-group-completion:{}".format(group_id)

    def _get(self, message_key: str, forget: bool) -> MResult:  # pragma: no cover
        """Get a result from the backend.  Subclasses may implement
        this method if they want to use the default, polling,
        implementation of get_result.
        """
        raise NotImplementedError("%(classname)r does not implement _get()" % {
            "classname": type(self).__name__,
        })

    def _store(self, message_key: str, result: typing.Dict, ttl: int) -> None:  # pragma: no cover
        """Store a result in the backend.  Subclasses may implement
        this method if they want to use the default implementation of
        set_result.
        """
        raise NotImplementedError("%(classname)r does not implement _store()" % {
            "classname": type(self).__name__,
        })
