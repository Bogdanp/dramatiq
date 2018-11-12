import time

import pytest

import remoulade
from remoulade.middleware import Retries
from remoulade.results import ResultMissing, Results, ResultTimeout, ErrorStored, FAILURE_RESULT


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_actors_can_store_results(stub_broker, stub_worker, backend, result_backends):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that stores results
    @remoulade.actor(store_results=True)
    def do_work():
        return 42

    # When I send that actor a message
    message = do_work.send()

    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # And wait for a result
    result = message.get_result(block=True)

    # Then the result should be what the actor returned
    assert result == 42


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_retrieving_a_result_can_raise_result_missing(stub_broker, stub_worker, backend, result_backends):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that sleeps for a long time before it stores a result
    @remoulade.actor(store_results=True)
    def do_work():
        time.sleep(0.2)
        return 42

    # When I send that actor a message
    message = do_work.send()

    # And get the result without blocking
    # Then a ResultMissing error should be raised
    with pytest.raises(ResultMissing):
        backend.get_result(message)


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_retrieving_a_result_can_time_out(stub_broker, stub_worker, backend, result_backends):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that sleeps for a long time before it stores a result
    @remoulade.actor(store_results=True)
    def do_work():
        time.sleep(0.2)
        return 42

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    # Then a ResultTimeout error should be raised
    with pytest.raises(ResultTimeout):
        backend.get_result(message, block=True, timeout=100)


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_messages_can_get_results_from_backend(stub_broker, stub_worker, backend, result_backends):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that stores a result
    @remoulade.actor(store_results=True)
    def do_work():
        return 42

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    # Then I should get that result back
    assert message.get_result(backend=backend, block=True) == 42


@pytest.mark.parametrize("backend", ["redis"])
def test_messages_can_get_results_from_inferred_backend(stub_broker, stub_worker, backend, result_backends):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that stores a result
    @remoulade.actor(store_results=True)
    def do_work():
        return 42

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    # Then I should get that result back
    assert message.get_result(block=True) == 42


def test_messages_can_fail_to_get_results_if_there_is_no_backend(stub_broker, stub_worker):
    # Given an actor that doesn't store results
    @remoulade.actor
    def do_work():
        return 42

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    # Then I should get a RuntimeError back
    with pytest.raises(RuntimeError):
        message.get_result()


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_result_default_before_retries(stub_broker, backend, result_backends, stub_worker):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    retries_index, results_index = None, None

    for i, middleware in enumerate(stub_broker.middleware):
        if isinstance(middleware, Retries):
            retries_index = i
        if isinstance(middleware, Results):
            results_index = i

    assert results_index is not None
    assert retries_index is not None
    # The Results middleware should be before the Retries middleware
    assert retries_index > results_index


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_raise_on_error(stub_broker, backend, result_backends, stub_worker):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that store a result and fail
    @remoulade.actor(store_results=True)
    def do_work():
        raise ValueError()

    # When I send that actor a message
    message = do_work.send()

    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # And wait for a result
    with pytest.raises(ErrorStored) as e:
        message.get_result(block=True)
    assert str(e.value) == 'ValueError()'


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_store_errors(stub_broker, backend, result_backends, stub_worker):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that store a result and fail
    @remoulade.actor(store_results=True)
    def do_work():
        raise ValueError()

    # When I send that actor a message
    message = do_work.send()

    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # And wait for a result
    assert message.get_result(block=True, raise_on_error=False) == FAILURE_RESULT


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_store_errors_after_no_more_retry(stub_broker, backend, result_backends, stub_worker):
    # Given that I have a database
    failures = []

    backend = result_backends[backend]
    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # Given an actor that stores results
    @remoulade.actor(max_retries=3, store_results=True, min_backoff=10, max_backoff=100)
    def do_work():
        failures.append(1)
        raise ValueError()

    # When I send that actor a message,
    message = do_work.send()

    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # I get an error
    with pytest.raises(Exception) as e:
        message.get_result(block=True)
    assert str(e.value) == 'ValueError()'

    # all the retries have been made
    assert sum(failures) == 4
