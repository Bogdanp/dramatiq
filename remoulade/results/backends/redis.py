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
from typing import List

import redis

from ..backend import DEFAULT_TIMEOUT, BackendResult, ForgottenResult, ResultBackend, ResultMissing, ResultTimeout


class RedisBackend(ResultBackend):
    """A result backend for Redis_.  This is the recommended result
    backend as waiting for a result is resource efficient.

    Parameters:
      namespace(str): A string with which to prefix result keys.
      encoder(Encoder): The encoder to use when storing and retrieving
        result data.  Defaults to :class:`.JSONEncoder`.
      client(Redis): An optional client.  If this is passed,
        then all other parameters are ignored.
      url(str): An optional connection URL.  If both a URL and
        connection paramters are provided, the URL is used.
      **parameters(dict): Connection parameters are passed directly
        to :class:`redis.Redis`.

    .. _redis: https://redis.io
    """

    def __init__(self, *, namespace="remoulade-results", encoder=None, client=None, url=None, **parameters):
        super().__init__(namespace=namespace, encoder=encoder)

        if url:
            parameters["connection_pool"] = redis.ConnectionPool.from_url(url)

        self.client = client or redis.Redis(**parameters)

    def get_result(self, message, *, block=False, timeout=None, forget=False, raise_on_error=True):
        """Get a result from the backend.

        Warning:
          Sub-second timeouts are not respected by this backend.

        Parameters:
          message(Message)
          block(bool): Whether or not to block until a result is set.
          timeout(int): The maximum amount of time, in ms, to wait for
            a result when block is True.  Defaults to 10 seconds.
          forget(bool): Whether or not the result need to be kept.
          raise_on_error(bool): raise an error if the result stored in
            an error

        Raises:
          ResultMissing: When block is False and the result isn't set.
          ResultTimeout: When waiting for a result times out.

        Returns:
          object: The result.
        """
        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        message_key = self.build_message_key(message)
        timeout = int(timeout / 1000)
        if block and timeout > 0:
            if forget:
                _, data = self.client.brpop(message_key, timeout=timeout)
                self.client.lpush(message_key, self.encoder.encode(ForgottenResult.asdict()))
            else:
                data = self.client.brpoplpush(message_key, message_key, timeout)

            if data is None:
                raise ResultTimeout(message)

        else:
            if forget:
                with self.client.pipeline() as pipe:
                    pipe.rpop(message_key)
                    pipe.lpush(message_key, self.encoder.encode(ForgottenResult.asdict()))
                    data = pipe.execute()[0]
            else:
                data = self.client.rpoplpush(message_key, message_key)

        if data is None:
            if block:
                raise ResultTimeout(message)
            else:
                raise ResultMissing(message)

        result = BackendResult(**self.encoder.decode(data))
        return self.process_result(result, raise_on_error)

    def _store(self, message_key, result, ttl):
        with self.client.pipeline() as pipe:
            pipe.delete(message_key)
            pipe.lpush(message_key, self.encoder.encode(result))
            pipe.pexpire(message_key, ttl)
            pipe.execute()

    def increment_group_completion(self, group_id: str) -> int:
        # there should be a ttl
        ttl = 600  # 10 min ?
        group_completion_key = self.build_group_completion_key(group_id)
        with self.client.pipeline() as pipe:
            pipe.incr(group_completion_key)
            pipe.expire(group_completion_key, ttl)
            group_completion = pipe.execute()[0]

        return group_completion

    def get_status(self, message_ids: List[str]) -> int:
        return self.client.exists(*[self.build_message_key(message_id) for message_id in message_ids])
