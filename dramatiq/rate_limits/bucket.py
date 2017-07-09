import enum
import time

from .rate_limiter import RateLimiter


class Bucket(enum.Enum):
    """The supported buckets for :class:`.BucketRateLimiter`.
    """

    Second = enum.auto()
    Minute = enum.auto()
    Hour = enum.auto()
    Day = enum.auto()


BUCKET_TO_SECONDS = {
    Bucket.Second: 1,
    Bucket.Minute: 60,
    Bucket.Hour: 3600,
    Bucket.Day: 86400,
}


class BucketRateLimiter(RateLimiter):
    """A rate limiter that ensures that only `n` operations may happen
    over some interval.

    Parameters:
      backend(RateLimiterBackend): The backend to use.
      key(str): The key to rate limit on.
      limit(int): The maximum number of operations per bucket per key.
      bucket(Bucket): The interval over which to rate limit operations.
    """

    def __init__(self, backend, key, *, limit=1, bucket=Bucket.Second):
        assert limit >= 1, "limit must be positive"
        assert bucket in Bucket, "bucket must be one of the predefined buckets"

        super().__init__(backend, key)
        self.limit = limit
        self.bucket = bucket
        self.bucket_seconds = seconds = BUCKET_TO_SECONDS[bucket]
        self.bucket_millis = seconds * 1000

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
