import time

from threading import Lock

from ..backend import RateLimiterBackend


class StubBackend(RateLimiterBackend):
    """An in-memory rate limiter backend.  For use in unit tests.
    """

    def __init__(self):
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

            values = sum(self._get(k, default=0) for k in keys)
            total = amount + values
            if total > maximum:
                return False

            return self._put(key, value, ttl)

    def _get(self, key, *, default=None):
        value, expiration = self.db.get(key, (None, None))
        if expiration and time.monotonic() < expiration:
            return value
        return default

    def _put(self, key, value, ttl):
        self.db[key] = (value, time.monotonic() + ttl / 1000)
        return True
