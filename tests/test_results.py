import dramatiq
import pytest
import time

from dramatiq.results import Missing, Results


@pytest.mark.parametrize("backend", ["memcached", "redis"])
def test_actors_can_store_results(stub_broker, stub_worker, backend, result_backends):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that stores results
    @dramatiq.actor(store_results=True)
    def do_work():
        return 42

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    result = backend.get_result(message, block=True)

    # Then the result should be what the actor returned
    assert result == 42


@pytest.mark.parametrize("backend", ["memcached", "redis"])
def test_retrieving_a_result_can_return_not_ready(stub_broker, stub_worker, backend, result_backends):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that sleeps for a long time before it stores a result
    @dramatiq.actor(store_results=True)
    def do_work():
        time.sleep(0.2)
        return 42

    # When I send that actor a message
    message = do_work.send()

    # And get the result without blocking
    result = backend.get_result(message)

    # Then the result should be Missing
    assert result is Missing


@pytest.mark.parametrize("backend", ["memcached", "redis"])
def test_retrieving_a_result_can_time_out(stub_broker, stub_worker, backend, result_backends):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that sleeps for a long time before it stores a result
    @dramatiq.actor(store_results=True)
    def do_work():
        time.sleep(0.2)
        return 42

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    result = backend.get_result(message, block=True, timeout=100)

    # Then the result should be Missing
    assert result is Missing
