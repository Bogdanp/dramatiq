import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from dramatiq.rate_limits import Barrier


def test_barrier(rate_limiter_backend):
    # Given that I have a barrier of two parties
    barrier = Barrier(rate_limiter_backend, "sequential-barrier", ttl=30000)
    assert barrier.create(parties=2)

    # When I try to recreate it
    # Then that should return False
    assert not barrier.create(parties=10)

    # The first party to wait should get back False
    assert not barrier.wait(block=False)

    # The second party to wait should get back True
    assert barrier.wait(block=False)


def test_barriers_can_block(rate_limiter_backend):
    # Given that I have a barrier of two parties
    barrier = Barrier(rate_limiter_backend, "sequential-barrier", ttl=30000)
    assert barrier.create(parties=2)

    # And I have a worker function that waits on the barrier and writes its timestamp
    times = []

    def worker():
        time.sleep(0.1)
        assert barrier.wait(timeout=1000)
        times.append(time.monotonic())

    try:
        # When I run those workers
        with ThreadPoolExecutor(max_workers=8) as e:
            for future in [e.submit(worker), e.submit(worker)]:
                future.result()
    except NotImplementedError:
        pytest.skip("Waiting is not supported under this backend.")

    # Then their execution times should be really close to one another
    assert abs(times[0] - times[1]) <= 0.01


def test_barriers_can_timeout(rate_limiter_backend):
    # Given that I have a barrier of two parties
    barrier = Barrier(rate_limiter_backend, "sequential-barrier", ttl=30000)
    assert barrier.create(parties=2)

    try:
        # When I wait on the barrier with a timeout
        # Then I should get False back
        assert not barrier.wait(timeout=1000)
    except NotImplementedError:
        pytest.skip("Waiting is not supported under this backend.")
