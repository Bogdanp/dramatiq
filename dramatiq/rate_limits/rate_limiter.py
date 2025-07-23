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

from contextlib import contextmanager

from ..errors import RateLimitExceeded


class RateLimiter:
    """ABC for rate limiters.

    Examples:

      >>> from dramatiq.rate_limits.backends import RedisBackend

      >>> backend = RedisBackend()
      >>> limiter = ConcurrentRateLimiter(backend, "distributed-mutex", limit=1)

      >>> with limiter.acquire(raise_on_failure=False) as acquired:
      ...     if not acquired:
      ...         print("Mutex not acquired.")
      ...         return
      ...
      ...     print("Mutex acquired.")

    Parameters:
      backend(RateLimiterBackend): The rate limiting backend to use.
      key(str): The key to rate limit on.
    """

    def __init__(self, backend, key):
        self.backend = backend
        self.key = key

    def _acquire(self):  # pragma: no cover
        raise NotImplementedError

    def _release(self):  # pragma: no cover
        raise NotImplementedError

    @contextmanager
    def acquire(self, *, raise_on_failure=True):
        """Attempt to acquire a slot under this rate limiter.

        Parameters:
          raise_on_failure(bool): Whether or not failures should raise an
            exception.  If this is false, the context manager will instead
            return a boolean value representing whether or not the rate
            limit slot was acquired.

        Returns:
          bool: Whether or not the slot could be acquired.
        """
        acquired = False

        try:
            acquired = self._acquire()
            if raise_on_failure and not acquired:
                raise RateLimitExceeded("rate limit exceeded for key %(key)r" % vars(self))

            yield acquired
        finally:
            if acquired:
                self._release()
