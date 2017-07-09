import time

from .rate_limiter import RateLimiter


class BucketRateLimiter(RateLimiter):
    """A rate limiter that ensures that only up to `limit` operations
    may happen over some time interval.

    Examples:

      Up to 10 operations every second:

      >>> BucketRateLimiter(backend, "some-key", limit=10, bucket=1)

      Up to 1 operation every minute:

      >>> BucketRateLimiter(backend, "some-key", limit=1, bucket=60)

    Warning:

      Bucket rate limits are cheap to maintain but are susceptible to
      burst "attacks".  Given a bucket rate limit of 100/minute, an
      attacker could make a burst of calls in the last and first
      second of every minute.

      For a rate limiter that doesn't have this problem (but is more
      expensive to maintain), see :class:`WindowRateLimiter`.

    Parameters:
      backend(RateLimiterBackend): The backend to use.
      key(str): The key to rate limit on.
      limit(int): The maximum number of operations per bucket per key.
      bucket(int): The bucket interval in *seconds*.
    """

    def __init__(self, backend, key, *, limit=1, bucket=1):
        assert limit >= 1, "limit must be positive"

        super().__init__(backend, key)
        self.limit = limit
        self.bucket = bucket
        self.bucket_seconds = bucket
        self.bucket_millis = bucket * 1000

    @property
    def current_timestamp(self):
        timestamp = int(time.time())
        remainder = timestamp % self.bucket_seconds
        return timestamp - remainder

    @property
    def current_key(self):
        return f"{self.key}@{self.current_timestamp}"

    def _acquire(self):
        added = self.backend.add(self.current_key, 1, ttl=self.bucket_millis)
        if added:
            return True

        return self.backend.incr(self.current_key, 1, maximum=self.limit, ttl=self.bucket_millis)

    def _release(self):
        pass
