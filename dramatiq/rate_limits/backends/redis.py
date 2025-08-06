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

from pathlib import Path

import redis

from ..backend import RateLimiterBackend

_SCRIPTS = {
    path.stem: path.read_text()
    for path in (Path(__file__).parent / "redis").glob("*.lua")
}


class RedisBackend(RateLimiterBackend):
    """A rate limiter backend for Redis_.

    Parameters:
      client(Redis): An optional client.  If this is passed,
        then all other parameters are ignored.
      url(str): An optional connection URL.  If both a URL and
        connection parameters are provided, the URL is used.
      **parameters: Connection parameters are passed directly
        to :class:`redis.Redis`.

    .. _redis: https://redis.io
    """

    def __init__(self, *, client=None, url=None, **parameters):
        if url is not None:
            parameters["connection_pool"] = redis.ConnectionPool.from_url(url)

        self.client = client or redis.Redis(**parameters)
        self.scripts = {
            name: self.client.register_script(text) for name, text in _SCRIPTS.items()
        }

    def add(self, key, value, ttl):
        return bool(self.client.set(key, value, px=ttl, nx=True))

    def incr(self, key, amount, maximum, ttl):
        incr_up_to = self.scripts["incr_up_to"]
        return incr_up_to([key], [amount, maximum, ttl]) == 1

    def decr(self, key, amount, minimum, ttl):
        decr_down_to = self.scripts["decr_down_to"]
        return decr_down_to([key], [amount, minimum, ttl]) == 1

    def incr_and_sum(self, key, keys, amount, maximum, ttl):
        incr_up_to_with_sum_check = self.scripts["incr_up_to_with_sum_check"]
        return incr_up_to_with_sum_check([key, *keys()], [amount, maximum, ttl]) == 1

    def wait(self, key, timeout):
        assert timeout is None or timeout >= 1000, "wait timeouts must be >= 1000"
        event = self.client.brpoplpush(key, key, (timeout or 0) // 1000)
        return event == b"x"

    def wait_notify(self, key, ttl):
        with self.client.pipeline() as pipe:
            pipe.rpush(key, b"x")
            pipe.pexpire(key, ttl)
            pipe.execute()
