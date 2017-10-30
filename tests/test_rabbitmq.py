import dramatiq
import os
import pytest
import time

from dramatiq import Message
from dramatiq.common import current_millis
from dramatiq.errors import ConnectionClosed
from unittest.mock import Mock


def test_rabbitmq_actors_can_be_sent_messages(rabbitmq_broker, rabbitmq_random_queue, rabbitmq_worker):
    # Given that I have a database
    database = {}

    # And an actor that can write data to that database
    @dramatiq.actor(queue_name=rabbitmq_random_queue)
    def put(key, value):
        database[key] = value

    # If I send that actor many async messages
    for i in range(100):
        assert put.send(f"key-{i}", i)

    # And I give the workers time to process the messages
    rabbitmq_broker.join(rabbitmq_random_queue)
    rabbitmq_worker.join()

    # I expect the database to be populated
    assert len(database) == 100


def test_rabbitmq_actors_retry_with_backoff_on_failure(rabbitmq_broker, rabbitmq_random_queue, rabbitmq_worker):
    # Given that I have a database
    failure_time, success_time = None, None

    # And an actor that fails the first time it's called
    @dramatiq.actor(min_backoff=1000, max_backoff=5000, queue_name=rabbitmq_random_queue)
    def do_work():
        nonlocal failure_time, success_time
        if not failure_time:
            failure_time = current_millis()
            raise RuntimeError("First failure.")
        else:
            success_time = current_millis()

    # If I send it a message
    do_work.send()

    # Then join on the queue
    rabbitmq_broker.join(rabbitmq_random_queue)
    rabbitmq_worker.join()

    # I expect backoff time to have passed between sucess and failure
    assert 500 <= success_time - failure_time <= 1500


def test_rabbitmq_actors_can_retry_multiple_times(rabbitmq_broker, rabbitmq_random_queue, rabbitmq_worker):
    # Given that I have a database
    attempts = []

    # And an actor that fails 3 times then succeeds
    @dramatiq.actor(max_backoff=1000, queue_name=rabbitmq_random_queue)
    def do_work():
        attempts.append(1)
        if sum(attempts) < 4:
            raise RuntimeError(f"Failure #{sum(attempts)}")

    # If I send it a message
    do_work.send()

    # Then join on the queue
    rabbitmq_broker.join(rabbitmq_random_queue)
    rabbitmq_worker.join()

    # I expect it to have been attempted 4 times
    assert sum(attempts) == 4


def test_rabbitmq_actors_can_have_their_messages_delayed(rabbitmq_broker, rabbitmq_random_queue, rabbitmq_worker):
    # Given that I have a database
    start_time, run_time = current_millis(), None

    # And an actor that records the time it ran
    @dramatiq.actor(queue_name=rabbitmq_random_queue)
    def record():
        nonlocal run_time
        run_time = current_millis()

    # If I send it a delayed message
    record.send_with_options(delay=1000)

    # Then join on the queue
    rabbitmq_broker.join(rabbitmq_random_queue)
    rabbitmq_worker.join()

    # I expect that message to have been processed at least delayed milliseconds later
    assert run_time - start_time >= 1000


def test_rabbitmq_actors_can_delay_messages_independent_of_each_other(
        rabbitmq_broker, rabbitmq_random_queue, rabbitmq_worker):
    # Given that I have a database
    results = []

    # And an actor that appends a number to the database
    @dramatiq.actor(queue_name=rabbitmq_random_queue)
    def append(x):
        results.append(x)

    # If I send it a delayed message
    append.send_with_options(args=(1,), delay=1500)

    # And then another delayed message with a smaller delay
    append.send_with_options(args=(2,), delay=1000)

    # Then join on the queue
    rabbitmq_broker.join(rabbitmq_random_queue)
    rabbitmq_worker.join()

    # I expect the latter message to have been run first
    assert results == [2, 1]


def test_rabbitmq_actors_can_have_retry_limits(rabbitmq_broker, rabbitmq_random_queue, rabbitmq_worker):
    # Given that I have an actor that always fails
    @dramatiq.actor(max_retries=0, queue_name=rabbitmq_random_queue)
    def do_work():
        raise RuntimeError("failed")

    # If I send it a message
    do_work.send()

    # Then join on its queue
    rabbitmq_broker.join(rabbitmq_random_queue)
    rabbitmq_worker.join()

    # I expect the message to get moved to the dead letter queue
    _, _, xq_count = rabbitmq_broker.get_queue_message_counts(rabbitmq_random_queue)
    assert xq_count == 1


def test_rabbitmq_messages_belonging_to_missing_actors_are_rejected(
        rabbitmq_broker, rabbitmq_random_queue, rabbitmq_worker):
    # Given that I have a broker without actors
    # If I send it a message
    message = Message(
        queue_name=rabbitmq_random_queue,
        actor_name="some-actor",
        args=(), kwargs={},
        options={},
    )
    rabbitmq_broker.declare_queue(rabbitmq_random_queue)
    rabbitmq_broker.enqueue(message)

    # Then join on the queue
    rabbitmq_broker.join(rabbitmq_random_queue)
    rabbitmq_worker.join()

    # I expect the message to end up on the dead letter queue
    _, _, dead = rabbitmq_broker.get_queue_message_counts(rabbitmq_random_queue)
    assert dead == 1


def test_rabbitmq_broker_reconnects_after_enqueue_failure(rabbitmq_broker, rabbitmq_random_queue):
    # Given that I have an actor
    @dramatiq.actor(queue_name=rabbitmq_random_queue)
    def do_nothing():
        pass

    # If I close my connection
    rabbitmq_broker.connection.close()

    # Then send my actor a message
    # I expect the message to be enqueued
    assert do_nothing.send()

    # And the connection be reopened
    assert rabbitmq_broker.connection.is_open


@pytest.mark.skipif(os.getenv("TRAVIS") == "1", reason="test skipped on Travis")
def test_rabbitmq_workers_handle_rabbit_failures_gracefully(rabbitmq_broker, rabbitmq_random_queue, rabbitmq_worker):
    # Given that I have an attempts database
    attempts = []

    # And an actor that adds 1 to the attempts database
    @dramatiq.actor(queue_name=rabbitmq_random_queue)
    def do_work():
        attempts.append(1)
        time.sleep(1)

    # If I send that actor a delayed message
    do_work.send_with_options(delay=1000)

    # If I stop the RabbitMQ app
    assert os.system("rabbitmqctl stop_app") >> 8 == 0

    # Then start the app back up
    assert os.system("rabbitmqctl start_app") >> 8 == 0

    # And join on the queue
    del rabbitmq_broker.channel
    del rabbitmq_broker.connection
    rabbitmq_broker.join(do_work.queue_name)
    rabbitmq_worker.join()

    # I expect the work to have been attempted at least once
    assert sum(attempts) >= 1


def test_rabbitmq_raises_an_exception_when_delaying_messages_for_too_long(rabbitmq_broker):
    # Given that I have an actor
    @dramatiq.actor
    def do_nothing():
        pass

    # If I try to send it a delayed message farther than 7 days into the future
    # I expect it to raise a value error
    with pytest.raises(ValueError):
        do_nothing.send_with_options(delay=7 * 86400 * 1000 + 1)


def test_rabbitmq_connections_can_be_deleted_multiple_times(rabbitmq_broker):
    del rabbitmq_broker.connection
    del rabbitmq_broker.connection


def test_rabbitmq_channels_can_be_deleted_multiple_times(rabbitmq_broker):
    del rabbitmq_broker.channel
    del rabbitmq_broker.channel


def test_rabbitmq_consumers_ignore_unknown_messages_in_ack_and_nack(rabbitmq_broker):
    # Given that I have a RabbitmqConsumer
    consumer = rabbitmq_broker.consume("default")

    # If I attempt to ack a Message that wasn't consumed off of it
    # I expect nothing to happen
    assert consumer.ack(Mock(_tag=1)) is None

    # Likewise for nack
    assert consumer.nack(Mock(_tag=1)) is None
