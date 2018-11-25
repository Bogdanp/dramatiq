import pytest

from dramatiq.barrier import Barrier, BarrierAbort


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_barrier(backend, barrier_backends):
    backend = rate_limiter_backends[backend]

    # Declare a barrier with a ttl of 30 seconds
    barrier = Barrier(backend, "sequential-barrier", ttl=30000)

    # Create the barrier with 2 parties in the group
    assert barrier.create(parties=2)

    # Attempting to recreate the barrier should fail
    assert not barrier.create(parties=10)

    # The first task should get False
    assert not barrier.wait()

    # The last task should get True
    assert barrier.wait()

    # Aborting makes the barrier raise if used
    barrier = Barrier(backend, "abort-barrier", ttl=30000)
    barrier.create(parties=2)
    barrier.abort()
    with pytest.raises(BarrierAbort):
        self.wait()

    # But we can also avoid raising
    barrier = Barrier(backend, "abort-barrier", ttl=30000)
    barrier.create(parties=2)
    barrier.abort()
    assert not self.wait(raise_on_abort=False)
