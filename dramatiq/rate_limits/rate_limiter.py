from contextlib import contextmanager

from ..errors import RateLimitExceeded


class RateLimiter:
    """ABC for rate limiters.

    Examples:

      >>> from dramatiq.rate_limits.backends import RedisBackend

      >>> backend = RedisBackend()
      >>> limiter = ConcurrentRateLimiter(backend, "distributed-mutex", limit=1)

      >>> with limiter.acquire(raise_on_failure=False) as acquired:
      ...   if not acquired:
      ...     print("Mutex not acquired.")
      ...     return
      ...
      ...   print("Mutex acquired.")

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
                raise RateLimitExceeded(f"rate limit exceeded for key {self.key!r}")

            yield acquired
        finally:
            if acquired:
                self._release()
