import itertools
import time
from unittest.mock import patch

import pytest

import dramatiq
from dramatiq.errors import Retry


def test_actors_retry_on_failure(stub_broker, stub_worker):
    # Given that I have a database
    failures, successes = [], []

    # And an actor that fails the first time it's called
    @dramatiq.actor(min_backoff=100, max_backoff=500)
    def do_work():
        if sum(failures) == 0:
            failures.append(1)
            raise RuntimeError("First failure.")
        else:
            successes.append(1)

    # If I send it a message
    do_work.send()

    # Then join on the queue
    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # I expect successes
    assert sum(successes) == 1


def test_actors_retry_a_max_number_of_times_on_failure(stub_broker, stub_worker):
    # Given that I have a database
    attempts = []

    # And an actor that fails every time
    @dramatiq.actor(max_retries=3, min_backoff=100, max_backoff=500)
    def do_work():
        attempts.append(1)
        raise RuntimeError("failure")

    # When I send it a message
    do_work.send()

    # And join on the queue
    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # Then I expect 4 attempts to have occurred
    assert sum(attempts) == 4


def test_actors_retry_for_a_max_time(stub_broker, stub_worker):
    # Given that I have a database
    attempts = []

    # And an actor that fails every time
    @dramatiq.actor(max_age=100, min_backoff=50, max_backoff=500)
    def do_work():
        attempts.append(1)
        raise RuntimeError("failure")

    # When I send it a message
    do_work.send()

    # And join on the queue
    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # Then I expect at least one attempt to have occurred
    assert sum(attempts) >= 1


def test_retry_exceptions_are_not_logged(stub_broker, stub_worker):
    # Given that I have an actor that raises Retry
    @dramatiq.actor(max_retries=0)
    def do_work():
        raise Retry()

    # And that I've mocked the logging class
    with patch("logging.Logger.error") as error_mock:
        # When I send that actor a message
        do_work.send()

        # And join on the queue
        stub_broker.join(do_work.queue_name)
        stub_worker.join()

        # Then no error should be logged
        error_messages = [args[0] for _, args, _ in error_mock.mock_calls]
        assert error_messages == []


def test_retry_exceptions_can_specify_a_delay(stub_broker, stub_worker):
    # Given that I have an actor that raises Retry
    attempts = 0
    timestamps = [time.monotonic()]

    @dramatiq.actor(max_retries=1)
    def do_work():
        nonlocal attempts
        attempts += 1
        timestamps.append(time.monotonic())
        if attempts == 1:
            raise Retry(delay=100)

    # When I send that actor a message
    do_work.send()

    # And join on the queue
    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # Then the actor should have been retried after 100ms
    assert 0.1 <= timestamps[-1] - timestamps[-2] < 0.15


def test_actors_can_be_assigned_zero_min_backoff(stub_broker, stub_worker):
    # Given that I have a database of timestamps
    timestamps = [time.monotonic()]

    # And an actor that fails ten times with zero backoff
    max_retries = 10

    @dramatiq.actor(min_backoff=0, max_retries=max_retries)
    def do_work():
        timestamps.append(time.monotonic())
        raise RuntimeError("failure")

    # When I send that actor a message
    do_work.send()

    # And join on the queue
    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # Then the actor should have retried 10 times without delay
    assert len(timestamps) == 2 + max_retries
    assert timestamps[-1] - timestamps[0] < 0.2


def test_actors_can_be_assigned_zero_max_backoff(stub_broker, stub_worker):
    # Given that I have a database of timestamps
    timestamps = [time.monotonic()]

    # And an actor that fails ten times with zero backoff
    max_retries = 10

    @dramatiq.actor(max_backoff=0, max_retries=max_retries)
    def do_work():
        timestamps.append(time.monotonic())
        raise RuntimeError("failure")

    # When I send that actor a message
    do_work.send()

    # And join on the queue
    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # Then the actor should have retried 10 times without delay
    assert len(timestamps) == 2 + max_retries
    assert timestamps[-1] - timestamps[0] < 0.2


def test_actor_messages_can_be_assigned_zero_min_backoff(stub_broker, stub_worker):
    # Given that I have a database of timestamps
    timestamps = [time.monotonic()]

    # And an actor that fails ten times with large backoff
    max_retries = 10

    @dramatiq.actor(min_backoff=10000, max_retries=max_retries)
    def do_work():
        timestamps.append(time.monotonic())
        raise RuntimeError("failure")

    # When I send that actor a message with zero min_backoff
    do_work.send_with_options(min_backoff=0)

    # And join on the queue
    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # Then the actor should have retried 10 times without delay
    assert len(timestamps) == 2 + max_retries
    assert timestamps[-1] - timestamps[0] < 0.2


def test_actor_messages_can_be_assigned_zero_max_backoff(stub_broker, stub_worker):
    # Given that I have a database of timestamps
    timestamps = [time.monotonic()]

    # And an actor that fails ten times with large backoff
    max_retries = 10

    @dramatiq.actor(min_backoff=10000, max_retries=max_retries)
    def do_work():
        timestamps.append(time.monotonic())
        raise RuntimeError("failure")

    # When I send that actor a message with zero max_backoff
    do_work.send_with_options(max_backoff=0)

    # And join on the queue
    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # Then the actor should have retried 10 times without delay
    assert len(timestamps) == 2 + max_retries
    assert timestamps[-1] - timestamps[0] < 0.2


@pytest.mark.parametrize("max_retries_message_option", (0, 4))
def test_actors_can_be_assigned_message_max_retries(stub_broker, stub_worker, max_retries_message_option):
    # Given that I have a database
    attempts = []

    # And an actor that fails every time and is retried with huge backoff
    @dramatiq.actor(max_retries=99, min_backoff=5000, max_backoff=50000)
    def do_work():
        attempts.append(1)
        raise RuntimeError("failure")

    # When I send it a message with tight backoff and custom max retries
    do_work.send_with_options(max_retries=max_retries_message_option, min_backoff=50, max_backoff=500)

    # And join on the queue
    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # Then I expect it to be retried as specified in the message options
    assert sum(attempts) == 1 + max_retries_message_option


def test_actors_can_conditionally_retry(stub_broker, stub_worker):
    # Given that I have a retry predicate
    def should_retry(retry_count, exception):
        return retry_count < 3 and isinstance(exception, RuntimeError)

    # And an actor that raises different types of errors
    attempts = []

    @dramatiq.actor(retry_when=should_retry, max_retries=0, min_backoff=100, max_backoff=100)
    def raises_errors(raise_runtime_error):
        attempts.append(1)
        if raise_runtime_error:
            raise RuntimeError("Runtime error")
        raise ValueError("Value error")

    # When I send that actor a message that makes it raise a value error
    raises_errors.send(False)

    # And wait for it
    stub_broker.join(raises_errors.queue_name)
    stub_worker.join()

    # Then I expect the actor not to retry
    assert sum(attempts) == 1

    # When I send that actor a message that makes it raise a runtime error
    attempts[:] = []
    raises_errors.send(True)

    # And wait for it
    stub_broker.join(raises_errors.queue_name)
    stub_worker.join()

    # Then I expect the actor to retry 3 times
    assert sum(attempts) == 4


class CustomException1(Exception):
    pass


class CustomException2(Exception):
    pass


@pytest.mark.parametrize("exn,throws", [
    [CustomException1, CustomException1],
    [CustomException1, (CustomException1,)],
    [CustomException2, (CustomException1, CustomException2)],
])
def test_actor_with_throws_logs_info_and_does_not_retry(stub_broker, stub_worker, exn, throws):
    # Given that I have a database
    attempts = []

    # And an actor that raises expected exceptions
    @dramatiq.actor(throws=throws)
    def do_work():
        attempts.append(1)
        if sum(attempts) == 1:
            raise exn("Expected Failure")

    # And that I've mocked the logging classes
    with patch("logging.Logger.error") as error_mock, \
         patch("logging.Logger.warning") as warning_mock, \
         patch("logging.Logger.info") as info_mock:
        # When I send that actor a message
        do_work.send()

        # And join on the queue
        stub_broker.join(do_work.queue_name)
        stub_worker.join()

        # Then no errors and or warnings should be logged
        assert [args[0] for _, args, _ in itertools.chain(error_mock.mock_calls, warning_mock.mock_calls)] == []

        # And two info messages should be logged
        info_messages = [args[0] for _, args, _ in info_mock.mock_calls]
        assert "Failed to process message %s with expected exception %s." in info_messages
        assert "Aborting message %r." in info_messages

        # And the message should not be retried
        assert sum(attempts) == 1


def test_message_contains_requeue_time_after_retry(stub_broker, stub_worker):

    # Given that I have a database
    requeue_timestamps = []

    stub_broker.add_middleware(dramatiq.middleware.CurrentMessage())
    max_retries = 2

    # And an actor that raises an exception and should be retried
    @dramatiq.actor(max_retries=max_retries, min_backoff=100, max_backoff=100)
    def do_work():

        current_message = dramatiq.middleware.CurrentMessage.get_current_message()

        if "requeue_timestamp" in current_message.options:
            requeue_timestamps.append(current_message.options["requeue_timestamp"])

        raise RuntimeError()

    message = do_work.send()

    # When I join on the queue and run the actor
    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # Then I expect correct number of requeue timestamps recorded
    assert len(requeue_timestamps) == max_retries

    # And that requeue timestamps are in increasing order
    assert all(requeue_timestamps[i] < requeue_timestamps[i + 1] for i in range(len(requeue_timestamps) - 1))

    # And that all requeue timestamps are larger than message timestamp
    assert all(requeue_time > message.message_timestamp for requeue_time in requeue_timestamps)


def test_on_retry_exhausted_is_sent(stub_broker, stub_worker):
    attempted_at = []
    called_at = []
    max_retries = 2

    @dramatiq.actor
    def handle_retries_exhausted(message_data, retry_info):
        called_at.append(time.monotonic())

    @dramatiq.actor(max_retries=max_retries, on_retry_exhausted=handle_retries_exhausted.actor_name)
    def do_work():
        attempted_at.append(time.monotonic())
        # Always request a retry
        raise Retry(delay=1)

    do_work.send()

    stub_broker.join(do_work.queue_name)
    stub_broker.join(handle_retries_exhausted.queue_name)
    stub_worker.join()

    # We should have the initial attempt + max_retries
    assert len(attempted_at) == max_retries + 1
    # And the exhausted handler should have been called.
    assert len(called_at) == 1


def test_on_retry_exhausted_is_not_sent_for_success(stub_broker, stub_worker):
    attempted_at = []
    called_at = []
    max_retries = 2

    @dramatiq.actor
    def handle_retries_exhausted(message_data, retry_info):
        called_at.append(time.monotonic())

    @dramatiq.actor(max_retries=max_retries, on_retry_exhausted=handle_retries_exhausted.actor_name)
    def do_work():
        attempted_at.append(time.monotonic())

    do_work.send()

    stub_broker.join(do_work.queue_name)
    stub_broker.join(handle_retries_exhausted.queue_name)
    stub_worker.join()

    # No retry should be required
    assert len(attempted_at) == 1
    # And the exhausted callback should have never been called
    assert len(called_at) == 0


def test_on_retry_exhausted_is_not_sent_for_eventual_success(stub_broker, stub_worker):
    attempted_at = []
    called_at = []
    max_retries = 2

    @dramatiq.actor
    def handle_retries_exhausted(message_data, retry_info):
        called_at.append(time.monotonic())

    @dramatiq.actor(max_retries=max_retries, on_retry_exhausted=handle_retries_exhausted.actor_name)
    def do_work():
        attempted_at.append(time.monotonic())
        if len(attempted_at) < 2:
            raise Retry(delay=1)

    do_work.send()

    stub_broker.join(do_work.queue_name)
    stub_broker.join(handle_retries_exhausted.queue_name)
    stub_worker.join()

    # The first retry should have succeeded
    assert len(attempted_at) == 2
    # So the exhausted callback should have never been called
    assert len(called_at) == 0
