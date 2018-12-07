import time

import pytest

import remoulade
from remoulade import Result
from remoulade.middleware import Retries
from remoulade.results import ResultMissing, Results, ResultTimeout, ErrorStored
from remoulade.results.backend import FailureResult
from remoulade.errors import ResultNotStored


@pytest.mark.parametrize("backend", ["redis", "stub"])
@pytest.mark.parametrize("forget", [True, False])
@pytest.mark.parametrize("block", [True, False])
def test_actors_can_store_results(stub_broker, stub_worker, backend, result_backends, forget, block):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that stores results
    @remoulade.actor(store_results=True)
    def do_work():
        return 42

    # And this actor is declared
    stub_broker.declare_actor(do_work)

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    if not block:
        stub_broker.join(do_work.queue_name)
        stub_worker.join()

    result = message.result.get(block=block, forget=forget)
    assert isinstance(message.result, Result)

    # Then the result should be what the actor returned
    assert result == 42


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_cannot_get_result_of_message_without_store_results(stub_broker, stub_worker, backend, result_backends):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that does not store results
    @remoulade.actor()
    def do_work():
        return 42

    # And this actor is declared
    stub_broker.declare_actor(do_work)

    # When I send that actor a message
    message = do_work.send()

    # I cannot access the result property of the message
    with pytest.raises(ResultNotStored) as e:
        message.result
    assert str(e.value) == 'There cannot be any result to an actor without store_results=True'


@pytest.mark.parametrize("backend", ["redis", "stub"])
@pytest.mark.parametrize("forget", [True, False])
def test_retrieving_a_result_can_raise_result_missing(stub_broker, stub_worker, backend, result_backends, forget):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that sleeps for a long time before it stores a result
    @remoulade.actor(store_results=True)
    def do_work():
        time.sleep(0.2)
        return 42

    # And this actor is declared
    stub_broker.declare_actor(do_work)

    # When I send that actor a message
    message = do_work.send()

    # And get the result without blocking
    # Then a ResultMissing error should be raised
    with pytest.raises(ResultMissing):
        backend.get_result(message, forget=forget)


@pytest.mark.parametrize("backend", ["redis", "stub"])
@pytest.mark.parametrize("forget", [True, False])
def test_retrieving_a_result_can_time_out(stub_broker, stub_worker, backend, result_backends, forget):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that sleeps for a long time before it stores a result
    @remoulade.actor(store_results=True)
    def do_work():
        time.sleep(0.2)
        return 42

    # And this actor is declared
    stub_broker.declare_actor(do_work)

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    # Then a ResultTimeout error should be raised
    with pytest.raises(ResultTimeout):
        backend.get_result(message, block=True, timeout=100, forget=forget)


@pytest.mark.parametrize("backend", ["redis", "stub"])
@pytest.mark.parametrize("forget", [True, False])
def test_messages_can_get_results_from_backend(stub_broker, stub_worker, backend, result_backends, forget):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that stores a result
    @remoulade.actor(store_results=True)
    def do_work():
        return 42

    # And this actor is declared
    stub_broker.declare_actor(do_work)

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    # Then I should get that result back
    assert message.result.get(block=True, forget=forget) == 42


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_messages_results_can_get_results_from_backend(stub_broker, stub_worker, backend, result_backends):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that stores a result
    @remoulade.actor(store_results=True)
    def do_work():
        return 42

    # And this actor is declared
    stub_broker.declare_actor(do_work)

    # When I send that actor a message
    message = do_work.send()

    # And create a message result
    result = Result(message_id=message.message_id)

    # And wait for a result
    # Then I should get that result back
    assert result.get(block=True) == 42


def test_messages_can_get_results_from_inferred_backend(stub_broker, stub_worker, redis_result_backend):
    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=redis_result_backend))

    # And an actor that stores a result
    @remoulade.actor(store_results=True)
    def do_work():
        return 42

    # And this actor is declared
    stub_broker.declare_actor(do_work)

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    # Then I should get that result back
    assert message.result.get(block=True) == 42


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
@pytest.mark.parametrize("block", [True, False])
def test_raise_on_error(stub_broker, backend, result_backends, stub_worker, block):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that store a result and fail
    @remoulade.actor(store_results=True)
    def do_work():
        raise ValueError()

    # And this actor is declared
    stub_broker.declare_actor(do_work)

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    if not block:
        stub_broker.join(do_work.queue_name)
        stub_worker.join()

    # It should raise an error
    with pytest.raises(ErrorStored) as e:
        message.result.get(block=block)
    assert str(e.value) == 'ValueError()'


@pytest.mark.parametrize("backend", ["redis", "stub"])
@pytest.mark.parametrize("block", [True, False])
def test_store_errors(stub_broker, backend, result_backends, stub_worker, block):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that store a result and fail
    @remoulade.actor(store_results=True)
    def do_work():
        raise ValueError()

    # And this actor is declared
    stub_broker.declare_actor(do_work)

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    if not block:
        stub_broker.join(do_work.queue_name)
        stub_worker.join()

    # Then I should get a FailureResult
    assert message.result.get(block=block, raise_on_error=False) == FailureResult


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

    # And this actor is declared
    stub_broker.declare_actor(do_work)

    # When I send that actor a message,
    message = do_work.send()

    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # I get an error
    with pytest.raises(Exception) as e:
        message.result.get(block=True)
    assert str(e.value) == 'ValueError()'

    # all the retries have been made
    assert sum(failures) == 4


@pytest.mark.parametrize("backend", ["redis", "stub"])
@pytest.mark.parametrize("block", [True, False])
def test_messages_can_get_results_and_forget(stub_broker, stub_worker, backend, result_backends, block):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that stores a result
    @remoulade.actor(store_results=True)
    def do_work():
        return 42

    # And this actor is declared
    stub_broker.declare_actor(do_work)

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    if not block:
        stub_broker.join(do_work.queue_name)
        stub_worker.join()

    # Then I should get that result back
    assert message.result.get(block=block, forget=True) == 42

    # If I ask again for the same result it should have been forgotten
    assert message.result.get() is None


@pytest.mark.parametrize("backend", ["redis", "stub"])
@pytest.mark.parametrize("error", [True, False])
def test_messages_can_get_completed(stub_broker, stub_worker, backend, result_backends, error):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that stores results
    @remoulade.actor(store_results=True)
    def do_work():
        if error:
            raise ValueError()
        else:
            return 42

    # And this actor is declared
    stub_broker.declare_actor(do_work)

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    result = message.result
    # we can get the completion
    assert result.completed

    result.get(forget=True, raise_on_error=False)

    # even after a forget
    assert result.completed
