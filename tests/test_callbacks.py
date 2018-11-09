from collections import Counter

import pytest

import remoulade


def test_actors_can_define_success_callbacks(stub_broker, stub_worker):
    # Given an actor that returns the sum of two numbers
    @remoulade.actor
    def add(x, y):
        return x + y

    # And an actor that takes in a number and stores it in a db
    db = []

    @remoulade.actor
    def save(_, result):
        db.append(result)

    # And these actors are declared
    stub_broker.declare_actor(add)
    stub_broker.declare_actor(save)

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
    @remoulade.actor(max_retries=0)
    def do_work():
        raise Exception()

    # And an actor that reports on exceptions
    exceptions = Counter()

    @remoulade.actor
    def report_exceptions(message_data, _):
        exceptions.update({message_data["actor_name"]})

    # And these actors are declared
    stub_broker.declare_actor(do_work)
    stub_broker.declare_actor(report_exceptions)

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
    @remoulade.actor
    def do_work():
        pass

    # And a non-actor callable
    def callback(*_):
        pass

    # And this actor is declared
    stub_broker.declare_actor(do_work)

    # When I try to set that callable as an on success callback
    # Then I should get back a TypeError
    with pytest.raises(TypeError):
        do_work.send_with_options(on_success=callback)
