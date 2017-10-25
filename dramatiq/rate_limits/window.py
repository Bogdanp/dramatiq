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

    def _acquire(self):
        timestamp = int(time.time())
        keys = [f"{self.key}@{timestamp - i}" for i in range(self.window)]

        # TODO: This is susceptible to drift because the keys are
        # never re-computed when CAS fails.
        return self.backend.incr_and_sum(
            keys[0], keys, 1,
            maximum=self.limit,
            ttl=self.window_millis,
        )

    def _release(self):
        pass
