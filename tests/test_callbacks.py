from collections import Counter

import pytest

import dramatiq


def test_actors_can_define_success_callbacks(stub_broker, stub_worker):
    # Given an actor that returns the sum of two numbers
    @dramatiq.actor
    def add(x, y):
        return x + y

    # And an actor that takes in a number and stores it in a db
    db = []

    @dramatiq.actor
    def save(message_data, result):
        db.append(result)

    # When I send the first actor a message and tell it to call the
    # second actor on success
    add.send_with_options(args=(1, 2), on_success=save)

    # And join on the broker and worker
    stub_broker.join(add.queue_name)
    stub_worker.join()

    # Then my db should contain the result
    assert db == [3]


def test_actors_can_define_failure_callbacks(stub_broker, stub_worker):
    # Given an actor that fails with an exception
    @dramatiq.actor(max_retries=0)
    def do_work():
        raise Exception()

    # And an actor that reports on exceptions
    exceptions = Counter()

    @dramatiq.actor
    def report_exceptions(message_data, exception_data):
        exceptions.update({message_data["actor_name"]})

    # When I send the first actor a message and tell it to call the
    # second actor on failure
    do_work.send_with_options(on_failure="report_exceptions")

    # And join on the broker and worker
    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # Then my db should contain the result
    assert exceptions[do_work.actor_name] == 1


def test_actor_callbacks_raise_type_error_when_given_a_normal_callable(stub_broker):
    # Given an actor that does nothing
    @dramatiq.actor
    def do_work():
        pass

    # And a non-actor callable
    def callback(message, res):
        pass

    # When I try to set that callable as an on success callback
    # Then I should get back a TypeError
    with pytest.raises(TypeError):
        do_work.send_with_options(on_success=callback)


def test_actor_callback_knows_correct_number_of_retries(stub_broker, stub_worker):
    MAX_RETRIES = 3
    attempts, retries = [], []

    # Given a callback that handles failure only after the last retry
    @dramatiq.actor
    def my_callback(message_data, exception_data):
        global handled
        handled = False
        retry = message_data["options"]["retries"]
        retries.append(retry)
        # Handle failure after last retry
        if retry > MAX_RETRIES:
            handled = True

    # And an actor that fails every time
    @dramatiq.actor(max_retries=MAX_RETRIES, max_backoff=100, on_failure=my_callback.actor_name)
    def do_work():
        attempts.append(1)
        raise RuntimeError("failure")

    # When I send it a message
    do_work.send()

    # And join on the queue
    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # Then I expect 4 attempts to have occurred
    assert len(attempts) == 4
    assert len(retries) == len(attempts)

    # And I expect the retry number to increase every time
    assert retries == [1, 2, 3, 4]
    # And I expect the callback to have handled the failure
    assert handled
