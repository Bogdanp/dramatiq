from __future__ import annotations

import time
from threading import Event
from unittest.mock import Mock, PropertyMock, patch

import pika.exceptions
import pytest

import dramatiq
from dramatiq import Worker
from dramatiq.brokers.rabbitmq import DEAD_MESSAGE_TTL, RabbitmqBroker
from dramatiq.common import current_millis
from dramatiq.middleware import Middleware

from .common import rabbitmq_server_version

# --- Unit tests (no broker connection required) ---


def test_quorum_broker_rejects_max_priority():
    # Quorum queues expose a built-in 0-31 priority range, so x-max-priority
    # is rejected by the server.  The broker should refuse it up front.
    with pytest.raises(RuntimeError):
        RabbitmqBroker(host="127.0.0.1", queue_type="quorum", max_priority=10)


def test_quorum_broker_omits_delivery_limit_by_default():
    # Given a quorum broker without an explicit delivery_limit
    broker = RabbitmqBroker(host="127.0.0.1", queue_type="quorum")

    # When I build the arguments for the main queue
    arguments = broker._build_queue_arguments("default")

    # Then it is declared as a quorum queue, without x-delivery-limit (so
    # RabbitMQ's own default applies) and without x-max-priority.
    assert arguments["x-queue-type"] == "quorum"
    assert "x-delivery-limit" not in arguments
    assert "x-max-priority" not in arguments


def test_quorum_broker_sets_delivery_limit_when_provided():
    # Given a quorum broker with an explicit delivery_limit
    broker = RabbitmqBroker(host="127.0.0.1", queue_type="quorum", delivery_limit=15)

    # Then the main queue carries it
    assert broker._build_queue_arguments("default")["x-delivery-limit"] == 15


def test_quorum_broker_declares_queues_with_correct_arguments():
    # Given a quorum broker with an explicit delivery_limit
    broker = RabbitmqBroker(host="127.0.0.1", queue_type="quorum", delivery_limit=15)

    captured = {}
    mock_channel = Mock()
    mock_channel.queue_declare.side_effect = lambda queue, durable, arguments: captured.__setitem__(queue, arguments)

    # When I declare the main, delay and dead-letter queues
    with patch.object(RabbitmqBroker, "channel", new_callable=PropertyMock, return_value=mock_channel):
        broker._declare_queue("default")
        broker._declare_dq_queue("default")
        broker._declare_xq_queue("default")

    # Then the main queue is quorum-typed and keeps the configured limit
    assert captured["default"]["x-queue-type"] == "quorum"
    assert captured["default"]["x-delivery-limit"] == 15
    assert captured["default"]["x-dead-letter-routing-key"] == "default.XQ"

    # And the delay queue is quorum-typed but always disables the limit,
    # since its messages are held unacked in memory until their eta passes.
    assert captured["default.DQ"]["x-queue-type"] == "quorum"
    assert captured["default.DQ"]["x-delivery-limit"] == -1

    # And the dead-letter queue is quorum-typed with the message TTL and no limit.
    assert captured["default.XQ"]["x-queue-type"] == "quorum"
    assert captured["default.XQ"]["x-message-ttl"] == DEAD_MESSAGE_TTL
    assert "x-delivery-limit" not in captured["default.XQ"]


# --- Integration tests (skipped automatically when RabbitMQ is unreachable) ---


def test_quorum_actors_can_be_sent_messages(quorum_rabbitmq_broker, quorum_rabbitmq_worker):
    # Given an actor that writes to a database
    database = {}

    @dramatiq.actor(queue_name="quorum_put")
    def put(key, value):
        database[key] = value

    # When I send it many messages
    for i in range(100):
        assert put.send("key-%d" % i, i)

    # And give the worker time to process them
    quorum_rabbitmq_broker.join(put.queue_name)
    quorum_rabbitmq_worker.join()

    # Then the database is populated
    assert len(database) == 100


def test_quorum_actors_retry_with_backoff_on_failure(quorum_rabbitmq_broker, quorum_rabbitmq_worker):
    failure_time, success_time = None, None
    succeeded = Event()

    # Given an actor that fails the first time it's called
    @dramatiq.actor(queue_name="quorum_retry", min_backoff=1000, max_backoff=5000)
    def do_work():
        nonlocal failure_time, success_time
        if not failure_time:
            failure_time = current_millis()
            raise RuntimeError("First failure.")
        else:
            success_time = current_millis()
            succeeded.set()

    # When I send it a message
    do_work.send()

    # Then it eventually succeeds, after the backoff has elapsed
    succeeded.wait(timeout=30)
    assert success_time is not None
    assert 1000 <= success_time - failure_time <= (2000 + 200)


def test_quorum_actors_can_have_their_messages_delayed(quorum_rabbitmq_broker, quorum_rabbitmq_worker):
    start_time, run_time = current_millis(), None

    # Given an actor that records when it ran
    @dramatiq.actor(queue_name="quorum_delay")
    def record():
        nonlocal run_time
        run_time = current_millis()

    # When I send it a delayed message
    record.send_with_options(delay=1000)

    quorum_rabbitmq_broker.join(record.queue_name)
    quorum_rabbitmq_worker.join()

    # Then it ran at least the delay later
    assert run_time is not None
    assert run_time - start_time >= 1000


def test_quorum_actors_can_delay_messages_independent_of_each_other(quorum_rabbitmq_broker):
    results = []

    @dramatiq.actor(queue_name="quorum_delay_indep")
    def append(x):
        results.append(x)

    broker = quorum_rabbitmq_broker
    worker = Worker(broker, worker_threads=1)

    try:
        # Given two delayed messages, the later-sent one with the smaller delay
        append.send_with_options(args=(1,), delay=1500)
        append.send_with_options(args=(2,), delay=1000)

        worker.start()
        broker.join(append.queue_name, min_successes=20)
        worker.join()

        # Then the message with the smaller delay runs first
        assert results == [2, 1]
    finally:
        worker.stop()


def test_quorum_actors_can_have_retry_limits(quorum_rabbitmq_broker, quorum_rabbitmq_worker):
    # Given an actor that always fails and never retries
    @dramatiq.actor(queue_name="quorum_dlq", max_retries=0)
    def do_work():
        raise RuntimeError("failed")

    # When I send it a message
    do_work.send()

    quorum_rabbitmq_broker.join(do_work.queue_name)
    quorum_rabbitmq_worker.join()

    # Then it lands on the dead-letter queue
    _, _, xq_count = quorum_rabbitmq_broker.get_queue_message_counts(do_work.queue_name)
    assert xq_count == 1


def test_quorum_broker_declares_quorum_typed_queues(quorum_rabbitmq_broker):
    # Given a queue created by the quorum broker
    @dramatiq.actor(queue_name="quorum_typecheck")
    def do_work():
        pass

    do_work.send()

    # When I try to redeclare it as a classic queue
    # Then the server rejects it, proving the queue is quorum-typed.
    with pytest.raises(pika.exceptions.ChannelClosedByBroker):
        quorum_rabbitmq_broker.channel.queue_declare(
            do_work.queue_name,
            durable=True,
            arguments={"x-queue-type": "classic"},
        )


def test_quorum_broker_enqueues_messages_in_strict_priority_order(quorum_rabbitmq_broker):
    if rabbitmq_server_version(quorum_rabbitmq_broker) < (4, 3):
        pytest.skip("strict priorities on quorum queues require RabbitMQ 4.3+")

    max_priority = 10
    message_processing_order = []
    queue_name = "quorum_prioritized"

    # Given an actor that records the priority of each message it processes
    @dramatiq.actor(queue_name=queue_name)
    def do_work(message_priority):
        message_processing_order.append(message_priority)

    worker = Worker(quorum_rabbitmq_broker, worker_threads=1)
    worker.queue_prefetch = 1
    worker.start()
    worker.pause()

    try:
        # When I enqueue messages with increasing priorities while paused
        for priority in range(max_priority):
            do_work.send_with_options(args=(priority,), broker_priority=priority)

        worker.resume()
        quorum_rabbitmq_broker.join(queue_name, timeout=5000)
        worker.join()

        # Then they are processed highest-priority first
        assert message_processing_order == list(reversed(range(max_priority)))
    finally:
        worker.stop()


def test_quorum_delayed_messages_are_re_leased_before_consumer_timeout(quorum_rabbitmq_broker):
    # Given a broker whose delay-queue lease is far shorter than the delay,
    # the consumer must re-lease the held message several times before its
    # eta -- keeping long delays from tripping the consumer-ack timeout.
    broker = quorum_rabbitmq_broker
    broker.delay_queue_lease_ms = 1500

    delay_events = []

    class CountDelays(Middleware):
        def before_delay_message(self, broker, message):
            delay_events.append(message.message_id)

    broker.add_middleware(CountDelays())

    run_times = []

    @dramatiq.actor(queue_name="quorum_relay")
    def record():
        run_times.append(current_millis())

    worker = Worker(broker, worker_threads=1)
    try:
        # When I send a message delayed (5s) well beyond the lease (1.5s)
        start = current_millis()
        record.send_with_options(delay=5000)
        worker.start()

        # join() doesn't wait on unacked/in-flight delayed messages, so poll.
        deadline = current_millis() + 15000
        while current_millis() < deadline and not run_times:
            time.sleep(0.1)

        # Then it runs exactly once, at roughly its eta (not the lease time),
        assert len(run_times) == 1
        assert 5000 <= run_times[0] - start <= 9000
        # and it was re-leased at least once on the way there.
        assert len(delay_events) >= 2
    finally:
        worker.stop()
