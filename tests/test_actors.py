import dramatiq
import platform
import pytest
import time

from dramatiq import Message, Worker


_current_platform = platform.python_implementation()


def test_actors_can_be_defined(stub_broker):
    # Given that I've decorated a function with @actor
    @dramatiq.actor
    def add(x, y):
        return x + y

    # I expect that function to become an instance of Actor
    assert isinstance(add, dramatiq.Actor)


def test_actors_can_be_assigned_predefined_options(stub_broker):
    # Given that I have a stub broker with the retries middleware
    # If I define an actor with a max_retries number
    @dramatiq.actor(max_retries=32)
    def add(x, y):
        return x + y

    # I expect the option to persist
    assert add.options["max_retries"] == 32


def test_actors_cannot_be_assigned_arbitrary_options(stub_broker):
    # Given that I have a stub broker
    # If I define an actor with a nonexistent option
    # I expect it to raise a ValueError
    with pytest.raises(ValueError):
        @dramatiq.actor(invalid_option=32)
        def add(x, y):
            return x + y


def test_actors_can_be_named(stub_broker):
    # Given that I've decorated a function with @actor and named it explicitly
    @dramatiq.actor(actor_name="foo")
    def add(x, y):
        return x + y

    # I expect the returned function to have that name
    assert add.actor_name == "foo"


def test_actors_can_be_assigned_custom_queues(stub_broker):
    # Given that I've decorated a function with @actor and given it an explicit queue
    @dramatiq.actor(queue_name="foo")
    def foo():
        pass

    # I expect the returned function to use that queue
    assert foo.queue_name == "foo"


def test_actors_fail_given_invalid_queue_names(stub_broker):
    # If I define an actor with an invalid queue name
    # I expect a ValueError to be raised
    with pytest.raises(ValueError):
        @dramatiq.actor(queue_name="$2@!@#")
        def foo():
            pass


def test_actors_can_be_called(stub_broker):
    # Given that I have an actor
    @dramatiq.actor
    def add(x, y):
        return x + y

    # If I call it directly,
    # I expect it to run synchronously
    assert add(1, 2) == 3


def test_actors_can_be_sent_messages(stub_broker):
    # Given that I have an actor
    @dramatiq.actor
    def add(x, y):
        return x + y

    # If I send it a message,
    # I expect it to enqueue a message
    enqueued_message = add.send(1, 2)
    enqueued_message_data = stub_broker.queues["default"].get(timeout=1)
    assert enqueued_message == Message.decode(enqueued_message_data)


def test_actors_can_perform_work(stub_broker, stub_worker):
    # Given that I have a database
    database = {}

    # And an actor that can write data to that database
    @dramatiq.actor
    def put(key, value):
        database[key] = value

    # If I send that actor many async messages
    for i in range(100):
        assert put.send(f"key-{i}", i)

    # Then join on the queue
    stub_broker.join(put.queue_name)

    # I expect the database to be populated
    assert len(database) == 100


def test_actors_can_perform_work_with_kwargs(stub_broker, stub_worker):
    # Given that I have a database
    results = []

    # And an actor
    @dramatiq.actor
    def add(x, y):
        results.append(x + y)

    # If I send it a message with kwargs
    add.send(x=1, y=2)

    # Then join on the queue
    stub_broker.join(add.queue_name)

    # I expect the database to be populated
    assert results == [3]


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

    # If I send it a message
    do_work.send()

    # Then join on the queue
    stub_broker.join(do_work.queue_name)

    # I expect successes
    assert sum(attempts) == 4


def test_actors_retry_for_a_max_time(stub_broker, stub_worker):
    # Given that I have a database
    attempts = []

    # And an actor that fails every time
    @dramatiq.actor(max_age=100, min_backoff=50, max_backoff=500)
    def do_work():
        attempts.append(1)
        raise RuntimeError("failure")

    # If I send it a message
    do_work.send()

    # Then join on the queue
    stub_broker.join(do_work.queue_name)

    # I expect successes
    assert sum(attempts) >= 1


@pytest.mark.skipif(_current_platform == "PyPy", reason="Time limits are not supported under PyPy.")
def test_actors_can_be_assigned_time_limits(stub_broker, stub_worker):
    # Given that I have a database
    attempts, successes = [], []

    # And an actor with a time limit
    @dramatiq.actor(max_retries=0, time_limit=1000)
    def do_work():
        attempts.append(1)
        time.sleep(2)
        successes.append(1)

    # If I send it a message
    do_work.send()

    # Then join on the queue
    stub_broker.join(do_work.queue_name)

    # I expect it to fail
    assert sum(attempts) == 1
    assert sum(successes) == 0


def test_actors_can_be_assigned_message_age_limits(stub_broker):
    # Given that I have a database
    runs = []

    # And an actor whose messages have an age limit
    @dramatiq.actor(max_age=100)
    def do_work():
        runs.append(1)

    # If I send it a message
    do_work.send()

    # And join on its queue after the age limit has passed
    time.sleep(0.1)
    worker = Worker(stub_broker, worker_timeout=100)
    worker.start()
    stub_broker.join(do_work.queue_name)
    worker.join()
    worker.stop()

    # I expect the message to have been skipped
    assert sum(runs) == 0


def test_actors_can_delay_messages_independent_of_each_other(stub_broker, stub_worker):
    # Given that I have a database
    results = []

    # And an actor that appends a number to the database
    @dramatiq.actor
    def append(x):
        results.append(x)

    # If I send it a delayed message
    append.send_with_options(args=(1,), delay=1500)

    # And then another delayed message with a smaller delay
    append.send_with_options(args=(2,), delay=1000)

    # Then join on the queue
    stub_broker.join(append.queue_name)
    stub_worker.join()

    # I expect the latter message to have been run first
    assert results == [2, 1]


def test_messages_belonging_to_missing_actors_are_rejected(stub_broker, stub_worker):
    # Given that I have a broker without actors
    # If I send it a message
    message = Message(
        queue_name="some-queue",
        actor_name="some-actor",
        args=(), kwargs={},
        options={},
    )
    stub_broker.declare_queue("some-queue")
    stub_broker.enqueue(message)

    # Then join on the queue
    stub_broker.join("some-queue")
    stub_worker.join()

    # I expect the message to end up on the dead letter queue
    assert stub_broker.dead_letters == [message]
