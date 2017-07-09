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
