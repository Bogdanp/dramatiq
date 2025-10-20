from __future__ import annotations

import logging
import os
import time
from threading import Event
from unittest.mock import Mock, patch

import pika.exceptions
import pytest

import dramatiq
from dramatiq import Message, Middleware, QueueJoinTimeout, Worker
from dramatiq.brokers.rabbitmq import (
    MAX_DECLARE_ATTEMPTS,
    RabbitmqBroker,
    _IgnoreScaryLogs,
)
from dramatiq.common import current_millis

from .common import (
    RABBITMQ_CREDENTIALS,
    RABBITMQ_PASSWORD,
    RABBITMQ_USERNAME,
    skip_unless_rabbit_mq,
)


@skip_unless_rabbit_mq
def test_rabbitmq_broker_can_be_passed_a_semicolon_separated_list_of_uris():
    # Given a string with a list of RabbitMQ connection URIs, including an invalid one
    # When I pass those URIs to RabbitMQ broker as a ;-separated string
    broker = RabbitmqBroker(
        url="amqp://127.0.0.1:55672;amqp://%s:%s@127.0.0.1" % (RABBITMQ_USERNAME, RABBITMQ_PASSWORD)
    )

    # The the broker should connect to the host that is up
    assert broker.connection


@skip_unless_rabbit_mq
def test_rabbitmq_broker_can_be_passed_a_list_of_uri_for_failover():
    # Given a string with a list of RabbitMQ connection URIs, including an invalid one
    # When I pass those URIs to RabbitMQ broker as a list
    broker = RabbitmqBroker(
        url=[
            "amqp://127.0.0.1:55672",
            "amqp://%s:%s@127.0.0.1" % (RABBITMQ_USERNAME, RABBITMQ_PASSWORD),
        ]
    )

    # The the broker should connect to the host that is up
    assert broker.connection


def test_rabbitmq_broker_raises_an_error_if_given_invalid_parameter_combinations():
    # Given that I have a RabbitmqBroker
    # When I try to give it both a connection URL and a list of connection parameters
    # Then a RuntimeError should be raised
    with pytest.raises(RuntimeError):
        RabbitmqBroker(
            url="amqp://127.0.0.1:5672",
            parameters=[dict(host="127.0.0.1", credentials=RABBITMQ_CREDENTIALS)],
        )

    # When I try to give it both a connection URL and pika connection parameters
    # Then a RuntimeError should be raised
    with pytest.raises(RuntimeError):
        RabbitmqBroker(host="127.0.0.1", url="amqp://127.0.0.1:5672")

    # When I try to give it both a list of parameters and individual flags
    # Then a RuntimeError should be raised
    with pytest.raises(RuntimeError):
        RabbitmqBroker(host="127.0.0.1", parameters=[dict(host="127.0.0.1")])


@skip_unless_rabbit_mq
def test_rabbitmq_broker_can_be_passed_a_list_of_parameters_for_failover():
    # Given a list of pika connection parameters including an invalid one
    parameters = [
        dict(host="127.0.0.1", port=55672),  # this will fail
        dict(host="127.0.0.1", credentials=RABBITMQ_CREDENTIALS),
    ]

    # When I pass those parameters to RabbitmqBroker
    broker = RabbitmqBroker(parameters=parameters)

    # Then I should still get a connection to the host that is up
    assert broker.connection


def test_rabbitmq_actors_can_be_sent_messages(rabbitmq_broker, rabbitmq_worker):
    # Given that I have a database
    database = {}

    # And an actor that can write data to that database
    @dramatiq.actor
    def put(key, value):
        database[key] = value

    # If I send that actor many async messages
    for i in range(100):
        assert put.send("key-%d" % i, i)

    # And I give the workers time to process the messages
    rabbitmq_broker.join(put.queue_name)
    rabbitmq_worker.join()

    # I expect the database to be populated
    assert len(database) == 100


def test_rabbitmq_actors_retry_with_backoff_on_failure(rabbitmq_broker, rabbitmq_worker):
    # Given that I have a database
    failure_time, success_time = None, None
    succeeded = Event()

    # And an actor that fails the first time it's called
    @dramatiq.actor(min_backoff=1000, max_backoff=5000)
    def do_work():
        nonlocal failure_time, success_time
        if not failure_time:
            failure_time = current_millis()
            raise RuntimeError("First failure.")
        else:
            success_time = current_millis()
            succeeded.set()

    # If I send it a message
    do_work.send()

    # Then wait for the actor to succeed
    succeeded.wait(timeout=30)

    # I expect backoff time to have passed between success and failure
    assert 1000 <= success_time - failure_time <= (2000 + 200)
    # The first backoff time should be 100-200% of min_backoff.
    # Add an extra 200 milliseconds to account for processing and to prevent flakiness.


def test_rabbitmq_actors_can_retry_multiple_times(rabbitmq_broker, rabbitmq_worker):
    # Given that I have a database
    attempts = []

    # And an actor that fails 3 times then succeeds
    @dramatiq.actor(max_backoff=1000)
    def do_work():
        attempts.append(1)
        if sum(attempts) < 4:
            raise RuntimeError("Failure #%d" % sum(attempts))

    # If I send it a message
    do_work.send()

    # Then join on the queue
    rabbitmq_broker.join(do_work.queue_name, min_successes=40)
    rabbitmq_worker.join()

    # I expect it to have been attempted 4 times
    assert sum(attempts) == 4


def test_rabbitmq_actors_can_have_their_messages_delayed(rabbitmq_broker, rabbitmq_worker):
    # Given that I have a database
    start_time, run_time = current_millis(), None

    # And an actor that records the time it ran
    @dramatiq.actor
    def record():
        nonlocal run_time
        run_time = current_millis()

    # If I send it a delayed message
    record.send_with_options(delay=1000)

    # Then join on the queue
    rabbitmq_broker.join(record.queue_name)
    rabbitmq_worker.join()

    # I expect that message to have been processed at least delayed milliseconds later
    assert run_time - start_time >= 1000


def test_rabbitmq_actors_can_delay_messages_independent_of_each_other(rabbitmq_broker):
    # Given that I have a database
    results = []

    # And an actor that appends a number to the database
    @dramatiq.actor
    def append(x):
        results.append(x)

    # And a worker
    broker = rabbitmq_broker
    worker = Worker(broker, worker_threads=1)

    try:
        # And I send it a delayed message
        append.send_with_options(args=(1,), delay=1500)

        # And then another delayed message with a smaller delay
        append.send_with_options(args=(2,), delay=1000)

        # Then resume the worker and join on the queue
        worker.start()
        broker.join(append.queue_name, min_successes=20)
        worker.join()

        # I expect the latter message to have been run first
        assert results == [2, 1]
    finally:
        worker.stop()


def test_rabbitmq_actors_can_have_retry_limits(rabbitmq_broker, rabbitmq_worker):
    # Given that I have an actor that always fails
    @dramatiq.actor(max_retries=0)
    def do_work():
        raise RuntimeError("failed")

    # If I send it a message
    do_work.send()

    # Then join on its queue
    rabbitmq_broker.join(do_work.queue_name)
    rabbitmq_worker.join()

    # I expect the message to get moved to the dead letter queue
    _, _, xq_count = rabbitmq_broker.get_queue_message_counts(do_work.queue_name)
    assert xq_count == 1


@skip_unless_rabbit_mq
def test_rabbitmq_broker_connections_are_lazy():
    # When I create an RMQ broker
    broker = RabbitmqBroker(
        host="127.0.0.1",
        max_priority=10,
        credentials=RABBITMQ_CREDENTIALS,
    )

    def get_connection():
        return getattr(broker.state, "connection", None)

    # Then it shouldn't immediately connect to the server
    assert get_connection() is None

    # When I declare a queue
    broker.declare_queue("some-queue")

    # Then it shouldn't connect either
    assert get_connection() is None

    # When I create a consumer on that queue
    broker.consume("some-queue", timeout=1)

    # Then it should connect
    assert get_connection() is not None


def test_rabbitmq_broker_stops_retrying_declaring_queues_when_max_attempts_reached(rabbitmq_broker):
    # Given that I have a rabbit instance that lost its connection
    with patch.object(
        rabbitmq_broker,
        "_declare_queue",
        side_effect=pika.exceptions.AMQPConnectionError,
    ) as mock_declare_queue:
        # When I declare and use an actor
        # Then a ConnectionClosed error should be raised
        with pytest.raises(dramatiq.errors.ConnectionClosed):

            @dramatiq.actor(queue_name="flaky_queue")
            def do_work():
                pass

            do_work.send()

    # check declare was attempted the max number of times.
    assert mock_declare_queue.call_count == MAX_DECLARE_ATTEMPTS


def test_rabbitmq_messages_belonging_to_missing_actors_are_rejected(rabbitmq_broker, rabbitmq_worker):
    # Given that I have a broker without actors
    # If I send it a message
    message = Message(
        queue_name="some-queue",
        actor_name="some-actor",
        args=(),
        kwargs={},
        options={},
    )
    rabbitmq_broker.declare_queue(message.queue_name)
    rabbitmq_broker.enqueue(message)

    # Then join on the queue
    rabbitmq_broker.join(message.queue_name)
    rabbitmq_worker.join()

    # I expect the message to end up on the dead letter queue
    _, _, dead = rabbitmq_broker.get_queue_message_counts(message.queue_name)
    assert dead == 1


def test_rabbitmq_broker_reconnects_after_enqueue_failure(rabbitmq_broker):
    # Given that I have an actor
    @dramatiq.actor
    def do_nothing():
        pass

    # If I close my connection
    rabbitmq_broker.connection.close()

    # Then send my actor a message
    # I expect the message to be enqueued
    assert do_nothing.send()

    # And the connection be reopened
    assert rabbitmq_broker.connection.is_open


def test_rabbitmq_workers_handle_rabbit_failures_gracefully(rabbitmq_broker, rabbitmq_worker):
    # Given that I have an attempts database
    attempts = []

    # And an actor that adds 1 to the attempts database
    @dramatiq.actor
    def do_work():
        attempts.append(1)
        time.sleep(1)

    # If I send that actor a delayed message
    do_work.send_with_options(delay=1000)

    # If I stop the RabbitMQ app
    os.system("rabbitmqctl stop_app")

    # Then start the app back up
    os.system("rabbitmqctl start_app")

    # And join on the queue
    del rabbitmq_broker.channel
    del rabbitmq_broker.connection
    rabbitmq_broker.join(do_work.queue_name)
    rabbitmq_worker.join()

    # I expect the work to have been attempted at least once
    assert sum(attempts) >= 1


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


def test_ignore_scary_logs_filter_ignores_logs():
    # Given a filter that ignores scary logs
    log_filter = _IgnoreScaryLogs("pika.adapters")

    # When I ask it to filter a log message that contains a scary message
    record = Mock()
    record.getMessage.return_value = "ConnectionError('Broken pipe')"

    # Then it should filter out that log message
    assert not log_filter.filter(record)

    # And when I ask it to filter a log message that doesn't
    record = Mock()
    record.getMessage.return_value = "Not scary"

    # Then it should ignore that log message
    assert log_filter.filter(record)


def test_rabbitmq_close_only_registers_ignore_filter_once():
    # Given a RabbitmqBroker
    broker = RabbitmqBroker()

    base_logger = logging.getLogger("pika.adapters.base_connection")
    blocking_logger = logging.getLogger("pika.adapters.blocking_connection")

    # And snapshots of the current filters
    original_base_filters = list(base_logger.filters)
    original_blocking_filters = list(blocking_logger.filters)

    try:
        # When I close the broker twice
        broker.close()
        broker.close()

        base_filters = [f for f in base_logger.filters if isinstance(f, _IgnoreScaryLogs)]
        blocking_filters = [f for f in blocking_logger.filters if isinstance(f, _IgnoreScaryLogs)]

        # Then only one ignore filter is registered per logger
        assert len(base_filters) == 1
        assert len(blocking_filters) == 1
    finally:
        # And the filters are removed after the test run
        # so they don't affect the global state.
        for log_filter in list(base_logger.filters):
            if log_filter not in original_base_filters:
                base_logger.removeFilter(log_filter)

        for log_filter in list(blocking_logger.filters):
            if log_filter not in original_blocking_filters:
                blocking_logger.removeFilter(log_filter)


def test_rabbitmq_broker_can_join_with_timeout(rabbitmq_broker, rabbitmq_worker):
    # Given that I have an actor that takes a long time to run
    @dramatiq.actor
    def do_work():
        time.sleep(1)

    # When I send that actor a message
    do_work.send()

    # And join on its queue with a timeout
    # Then I expect a QueueJoinTimeout to be raised
    with pytest.raises(QueueJoinTimeout):
        rabbitmq_broker.join(do_work.queue_name, timeout=500)


def test_rabbitmq_broker_can_flush_queues(rabbitmq_broker):
    # Given that I have an actor
    @dramatiq.actor
    def do_work():
        pass

    # When I send that actor a message
    do_work.send()

    # And then tell the broker to flush all queues
    rabbitmq_broker.flush_all()

    # And then join on the actors's queue
    # Then it should join immediately
    assert rabbitmq_broker.join(do_work.queue_name, min_successes=1, timeout=200) is None


def test_rabbitmq_broker_can_enqueue_messages_with_priority(rabbitmq_broker):
    max_priority = 10
    message_processing_order = []
    queue_name = "prioritized"

    # Given that I have an actor that store priorities
    @dramatiq.actor(queue_name=queue_name)
    def do_work(message_priority):
        message_processing_order.append(message_priority)

    worker = Worker(rabbitmq_broker, worker_threads=1)
    worker.queue_prefetch = 1
    worker.start()
    worker.pause()

    try:
        # When I send that actor messages with increasing priorities
        for priority in range(max_priority):
            do_work.send_with_options(args=(priority,), broker_priority=priority)

        # And then tell the broker to wait for all messages
        worker.resume()
        rabbitmq_broker.join(queue_name, timeout=5000)
        worker.join()

        # I expect the stored priorities to be saved in decreasing order
        assert message_processing_order == list(reversed(range(max_priority)))
    finally:
        worker.stop()


def test_rabbitmq_broker_retries_declaring_queues_when_connection_related_errors_occur(rabbitmq_broker):
    executed, declare_called = False, False
    original_declare = rabbitmq_broker._declare_queue

    def flaky_declare_queue(*args, **kwargs):
        nonlocal declare_called
        if not declare_called:
            declare_called = True
            raise pika.exceptions.AMQPConnectionError
        return original_declare(*args, **kwargs)

    # Given that I have a flaky connection to a rabbitmq server
    with patch.object(rabbitmq_broker, "_declare_queue", flaky_declare_queue):
        # When I declare an actor
        @dramatiq.actor(queue_name="flaky_queue")
        def do_work():
            nonlocal executed
            executed = True

        # And I send that actor a message
        do_work.send()

        # And wait for the worker to process the message
        worker = Worker(rabbitmq_broker, worker_threads=1)
        worker.start()

        try:
            rabbitmq_broker.join(do_work.queue_name, timeout=5000)
            worker.join()

            # Then the queue should eventually be declared and the message executed
            assert declare_called
            assert executed
        finally:
            worker.stop()


def test_rabbitmq_broker_retries_declaring_queues_when_declared_queue_disappears(rabbitmq_broker):
    executed = False

    # Given that I have an actor on a flaky queue
    flaky_queue_name = "flaky_queue"
    rabbitmq_broker.channel.queue_delete(flaky_queue_name)

    @dramatiq.actor(queue_name=flaky_queue_name)
    def do_work():
        nonlocal executed
        executed = True

    # When I start a server
    worker = Worker(rabbitmq_broker, worker_threads=1)
    worker.start()

    declared_ev = Event()

    class DeclaredMiddleware(Middleware):
        def after_declare_queue(self, broker, queue_name):
            if queue_name == flaky_queue_name:
                declared_ev.set()

    # I expect that queue to be declared
    rabbitmq_broker.add_middleware(DeclaredMiddleware())
    assert declared_ev.wait(timeout=5)

    # If I delete the queue
    rabbitmq_broker.channel.queue_delete(do_work.queue_name)
    with pytest.raises(pika.exceptions.ChannelClosedByBroker):
        rabbitmq_broker.channel.queue_declare(do_work.queue_name, passive=True)

    # And I send that actor a message
    do_work.send()
    try:
        rabbitmq_broker.join(do_work.queue_name, timeout=20000)
        worker.join()
    finally:
        worker.stop()

    # Then the queue should be declared and the message executed
    assert executed


def test_rabbitmq_messages_that_failed_to_decode_are_rejected(rabbitmq_broker, rabbitmq_worker):
    # Given that I have an Actor
    @dramatiq.actor(max_retries=0)
    def do_work(_):
        pass

    old_encoder = dramatiq.get_encoder()

    # And an encoder that may fail to decode
    class BadEncoder(type(old_encoder)):
        def decode(self, data):
            if "xfail" in str(data):
                raise RuntimeError("xfail")
            return super().decode(data)

    dramatiq.set_encoder(BadEncoder())

    try:
        # When I send a message that will fail to decode
        do_work.send("xfail")

        # And I join on the queue
        rabbitmq_broker.join(do_work.queue_name)
        rabbitmq_worker.join()

        # Then I expect the message to get moved to the dead letter queue
        q_count, dq_count, xq_count = rabbitmq_broker.get_queue_message_counts(do_work.queue_name)

        assert q_count == dq_count == 0
        assert xq_count == 1
    finally:
        dramatiq.set_encoder(old_encoder)


def test_rabbitmq_queues_only_contains_canonical_name(rabbitmq_broker, rabbitmq_worker):
    assert len(rabbitmq_broker.queues) == 0

    @dramatiq.actor
    def put():
        pass

    assert len(rabbitmq_broker.queues) == 1
    assert put.queue_name in rabbitmq_broker.queues
