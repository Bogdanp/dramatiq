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


class BarrierRateLimiter(RateLimiter):
    """A rate limiter that acquires after `parties` attempts.



    Examples:

      Create a barrier with three parties:

      >>> creator = BarrierRateLimiter(backend, "some-key", parties=3)
      >>> with creator.acquire(raise_on_failure=False) as acquired:
      ...     if not acquired:
      ...         raise RuntimeError("Barrier could not be created.")

      On an attempt:

      >>> limiter = BarrierRateLimiter(backend, "some-key")
      >>> with limiter.acquire(raise_on_failure=False) as acquired:
      ...     if acquired:
      ...         do_next_steps()

    Warning:

      Barrier rate limits will view successive attempts of the same
      message as if it were a different message. You almost certainly
      want to use `raise_on_failure=False` so that you can handle
      failure without re-queueing the message automatically.

    Parameters:
      backend(RateLimiterBackend): The backend to use.
      key(str): The key to rate limit on.
      parties(int): How many parties are required to reach the barrier.
      ttl(int): The time in milliseconds that keys may live for.
    """

    def __init__(self, backend, key, *, parties=None, ttl=600000):
        assert parties is None or parties >= 1, "parties must be positive"

        super().__init__(backend, key)
        self.parties = parties
        self.ttl = ttl

    def _acquire(self):
        if self.parties is not None:
            return self.backend.add(self.key, self.parties, ttl=self.ttl)
        return not self.backend.decr(self.key, 1, 1, ttl=self.ttl)

    def _release(self):
        pass
