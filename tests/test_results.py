import time

import pytest

import dramatiq
from dramatiq.results import ResultMissing, Results, ResultTimeout


def test_actors_can_store_results(stub_broker, stub_worker, result_backend):
    # Given a result backend
    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=result_backend))

    # And an actor that stores results
    @dramatiq.actor(store_results=True)
    def do_work():
        return 42

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    result = result_backend.get_result(message, block=True)

    # Then the result should be what the actor returned
    assert result == 42


def test_retrieving_a_result_can_raise_result_missing(stub_broker, stub_worker, result_backend):
    # Given a result backend
    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=result_backend))

    # And an actor that sleeps for a long time before it stores a result
    @dramatiq.actor(store_results=True)
    def do_work():
        time.sleep(0.2)
        return 42

    # When I send that actor a message
    message = do_work.send()

    # And get the result without blocking
    # Then a ResultMissing error should be raised
    with pytest.raises(ResultMissing):
        result_backend.get_result(message)


def test_retrieving_a_result_can_time_out(stub_broker, stub_worker, result_backend):
    # Given a result backend
    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=result_backend))

    # And an actor that sleeps for a long time before it stores a result
    @dramatiq.actor(store_results=True)
    def do_work():
        time.sleep(0.2)
        return 42

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    # Then a ResultTimeout error should be raised
    with pytest.raises(ResultTimeout):
        result_backend.get_result(message, block=True, timeout=100)


def test_messages_can_get_results_from_backend(stub_broker, stub_worker, result_backend):
    # Given a result backend
    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=result_backend))

    # And an actor that stores a result
    @dramatiq.actor(store_results=True)
    def do_work():
        return 42

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    # Then I should get that result back
    assert message.get_result(backend=result_backend, block=True) == 42


def test_messages_can_get_results_from_inferred_backend(stub_broker, stub_worker, result_backend):
    # Given a result backend
    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=result_backend))

    # And an actor that stores a result
    @dramatiq.actor(store_results=True)
    def do_work():
        return 42

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    # Then I should get that result back
    assert message.get_result(block=True) == 42


def test_messages_can_fail_to_get_results_if_there_is_no_backend(stub_broker, stub_worker):
    # Given an actor that doesn't store results
    @dramatiq.actor
    def do_work():
        return 42

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    # Then I should get a RuntimeError back
    with pytest.raises(RuntimeError):
        message.get_result()
