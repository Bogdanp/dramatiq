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

import redis

from ..backend import RateLimiterBackend


class RedisBackend(RateLimiterBackend):
    """A rate limiter backend for Redis_.

    Parameters:
      client(StrictRedis): An optional client.  If this is passed,
        then all other parameters are ignored.
      \**parameters(dict): Connection parameters are passed directly
        to :class:`redis.StrictRedis`.

    .. _redis: https://redis.io
    """

    def __init__(self, *, client=None, **parameters):
        self.client = client or redis.StrictRedis(**parameters)

    def add(self, key, value, ttl):
        return bool(self.client.set(key, value, px=ttl, nx=True))

    def incr(self, key, amount, maximum, ttl):
        with self.client.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(key)
                    value = int(pipe.get(key) or b"0")
                    value += amount
                    if value > maximum:
                        return False

                    pipe.multi()
                    pipe.set(key, value, px=ttl)
                    pipe.execute()
                    return True
                except redis.WatchError:
                    continue

    def decr(self, key, amount, minimum, ttl):
        with self.client.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(key)
                    value = int(pipe.get(key) or b"0")
                    value -= amount
                    if value < minimum:
                        return False

                    pipe.multi()
                    pipe.set(key, value, px=ttl)
                    pipe.execute()
                    return True
                except redis.WatchError:
                    continue

    def incr_and_sum(self, key, keys, amount, maximum, ttl):
        with self.client.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(key, *keys)
                    value = int(pipe.get(key) or b"0")
                    value += amount
                    if value > maximum:
                        return False

                    values = pipe.mget(keys)
                    total = amount + sum(int(n) for n in values if n)
                    if total > maximum:
                        return False

                    pipe.multi()
                    pipe.set(key, value, px=ttl)
                    pipe.execute()
                    return True
                except redis.WatchError:
                    continue
