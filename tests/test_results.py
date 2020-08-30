import time
from unittest.mock import patch

import pytest

import dramatiq
from dramatiq.message import Message
from dramatiq.results import ResultFailure, ResultMissing, Results, ResultTimeout


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


def test_actors_results_are_backwards_compatible(stub_broker, stub_worker, result_backend):
    # Given a result backend
    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=result_backend))

    # And an actor that stores results
    @dramatiq.actor(store_results=True)
    def do_work():
        return 42

    # And I have a result created using an old version of dramatiq
    message = do_work.message()
    message_key = result_backend.build_message_key(message)
    result_backend._store(message_key, 42, 3600000)

    # When I grab that result
    result = result_backend.get_result(message, block=True)

    # Then it should be unwrapped correctly
    assert result == 42


def test_actors_can_store_exceptions(stub_broker, stub_worker, result_backend):
    # Given a result backend
    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=result_backend))

    # And an actor that stores results
    @dramatiq.actor(store_results=True, max_retries=0)
    def do_work():
        raise RuntimeError("failed")

    # When I send that actor a message
    message = do_work.send()

    # And wait for a result
    # Then the result should be an exception
    with pytest.raises(ResultFailure) as e:
        result_backend.get_result(message, block=True)

    assert str(e.value) == "actor raised RuntimeError: failed"
    assert e.value.orig_exc_type == "RuntimeError"
    assert e.value.orig_exc_msg == "failed"


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


def test_messages_without_actor_not_crashing_lookup_options(stub_broker, redis_result_backend):
    message = Message(
        queue_name="default", actor_name="idontexist",
        args=(), kwargs={}, options={},
    )
    assert Results(backend=redis_result_backend).after_nack(stub_broker, message) is None


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


def test_actor_no_warning_when_returns_none(stub_broker, stub_worker):
    # Given that I've mocked the logging class
    with patch("logging.Logger.warning") as warning_mock:
        # And I have an actor that always returns None, and does not store results
        @dramatiq.actor
        def nothing():
            pass

        # When I send that actor a message
        nothing.send()

        # And wait for the message to get processed
        stub_broker.join(nothing.queue_name)
        stub_worker.join()

        # Then a warning should not be logged
        warning_messages = [args[0] for _, args, _ in warning_mock.mock_calls]
        assert not any("Consider adding the Results middleware" in x for x in warning_messages)


def test_actor_warning_when_returns_result_and_no_results_middleware_present(stub_broker, stub_worker):
    # Given that I've mocked the logging class
    with patch("logging.Logger.warning") as warning_mock:
        # And I have an actor that always returns 1, and does not store results
        @dramatiq.actor
        def always_1():
            return 1

        # When I send that actor a message
        always_1.send()

        # And wait for the message to get processed
        stub_broker.join(always_1.queue_name)
        stub_worker.join()

        # Then a warning should be logged
        warning_messages = [args[0] for _, args, _ in warning_mock.mock_calls]
        assert any("Consider adding the Results middleware" in x for x in warning_messages)


def test_actor_no_warning_when_returns_result_and_results_middleware_present(stub_broker, stub_worker, result_backend):
    # Given a result backend
    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=result_backend))
    # And that I've mocked the logging class
    with patch("logging.Logger.warning") as warning_mock:
        # And I have an actor that always returns 1, and does store results
        @dramatiq.actor(store_results=True)
        def always_1():
            return 1

        # When I send that actor a message
        always_1.send()

        # And wait for the message to get processed
        stub_broker.join(always_1.queue_name)
        stub_worker.join()

        # Then a warning should not be logged
        warning_messages = [args[0] for _, args, _ in warning_mock.mock_calls]
        assert not any("Consider adding the Results middleware" in x for x in warning_messages)
