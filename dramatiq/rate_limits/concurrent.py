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

from .rate_limiter import RateLimiter


class ConcurrentRateLimiter(RateLimiter):
    """A rate limiter that ensures that only `limit` concurrent
    operations may happen at the same time.

    Note:

      You can use a concurrent rate limiter of size 1 to get a
      distributed mutex.

    Parameters:
      backend(RateLimiterBackend): The backend to use.
      key(str): The key to rate limit on.
      limit(int): The maximum number of concurrent operations per key.
      ttl(int): The time in milliseconds that keys may live for.
    """

    def __init__(self, backend, key, *, limit=1, ttl=900000):
        assert limit >= 1, "limit must be positive"

        super().__init__(backend, key)
        self.limit = limit
        self.ttl = ttl

    def _acquire(self):
        added = self.backend.add(self.key, 1, ttl=self.ttl)
        if added:
            return True

        return self.backend.incr(self.key, 1, maximum=self.limit, ttl=self.ttl)

    def _release(self):
        return self.backend.decr(self.key, 1, minimum=0, ttl=self.ttl)
