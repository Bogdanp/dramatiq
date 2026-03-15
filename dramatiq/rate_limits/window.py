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

import time

from .rate_limiter import RateLimiter


class WindowRateLimiter(RateLimiter):
    """A rate limiter that ensures that only `limit` operations may
    happen over some sliding window.

    Note:

      Windows are in seconds rather that milliseconds.  This is
      different from most durations and intervals used in Dramatiq,
      because keeping metadata at the millisecond level is far too
      expensive for most use cases.

    Parameters:
      backend(RateLimiterBackend): The backend to use.
      key(str): The key to rate limit on.
      limit(int): The maximum number of operations per window per key.
      window(int): The window size in *seconds*.  The wider the
        window, the more expensive it is to maintain.
    """

    def __init__(self, backend, key, *, limit=1, window=1):
        assert limit >= 1, "limit must be positive"
        assert window >= 1, "window must be positive"

        super().__init__(backend, key)
        self.limit = limit
        self.window = window
        self.window_millis = window * 1000

    def _get_keys(self):
        timestamp = int(time.time())
        return ["%s@%s" % (self.key, timestamp - i) for i in range(self.window)]

    def _acquire(self):
        keys = self._get_keys()
        return self.backend.incr_and_sum(
            keys[0],
            self._get_keys,
            1,
            maximum=self.limit,
            ttl=self.window_millis,
        )

    def _release(self):
        pass
