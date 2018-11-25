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

import time
from collections import defaultdict
from threading import Condition, Lock

from ..backend import RateLimiterBackend


class StubBackend(RateLimiterBackend):
    """An in-memory rate limiter backend.  For use in unit tests.
    """

    def __init__(self):
        self.conditions = defaultdict(lambda: Condition(self.mutex))
        self.mutex = Lock()
        self.db = {}

    def add(self, key, value, ttl):
        with self.mutex:
            res = self._get(key)
            if res is not None:
                return False

            return self._put(key, value, ttl)

    def incr(self, key, amount, maximum, ttl):
        with self.mutex:
            value = self._get(key, default=0) + amount
            if value > maximum:
                return False

            return self._put(key, value, ttl)

    def decr(self, key, amount, minimum, ttl):
        with self.mutex:
            value = self._get(key, default=0) - amount
            if value < minimum:
                return False

            return self._put(key, value, ttl)

    def incr_and_sum(self, key, keys, amount, maximum, ttl):
        self.add(key, 0, ttl)
        with self.mutex:
            value = self._get(key, default=0) + amount
            if value > maximum:
                return False

            # TODO: Drop non-callable keys in Dramatiq v2.
            key_list = keys() if callable(keys) else keys
            values = sum(self._get(k, default=0) for k in key_list)
            total = amount + values
            if total > maximum:
                return False

            return self._put(key, value, ttl)

    def wait(self, key, timeout):
        cond = self.conditions[key]
        with cond:
            return cond.wait(timeout=timeout / 1000)

    def wait_notify(self, key, ttl):
        cond = self.conditions[key]
        with cond:
            cond.notify_all()

    def _get(self, key, *, default=None):
        value, expiration = self.db.get(key, (None, None))
        if expiration and time.monotonic() < expiration:
            return value
        return default

    def _put(self, key, value, ttl):
        self.db[key] = (value, time.monotonic() + ttl / 1000)
        return True
