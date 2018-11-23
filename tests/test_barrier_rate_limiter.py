import pytest

from dramatiq.rate_limits import BarrierRateLimiter


@pytest.mark.parametrize("backend", ["memcached", "redis", "stub"])
def test_barrier_rate_limiter_limits_to_attempt(backend, rate_limiter_backends):
    backend = rate_limiter_backends[backend]
    key = "sequential-barrier"

    # Create the barrier rate limiter
    creator = BarrierRateLimiter(backend, key, parties=2)
    with creator.acquire(raise_on_failure=False) as acquired:
        assert acquired
    # Ensure it doesn't overwrite
    with creator.acquire(raise_on_failure=False) as acquired:
        assert not acquired

    # Use the barrier rate limiter
    limiter = BarrierRateLimiter(backend, key)
    with limiter.acquire(raise_on_failure=False) as acquired:
        assert not acquired
    with limiter.acquire(raise_on_failure=False) as acquired:
        assert acquired
    with limiter.acquire(raise_on_failure=False) as acquired:
        assert acquired
