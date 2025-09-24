from __future__ import annotations

import time
from unittest import mock

import pytest
import redis

import dramatiq
from dramatiq import Message, QueueJoinTimeout
from dramatiq.brokers.redis import MAINTENANCE_SCALE, RedisBroker
from dramatiq.common import current_millis, dq_name, xq_name
from dramatiq.errors import ConnectionError

from .common import worker

LUA_MAX_UNPACK_SIZE = 7999


def test_redis_actors_can_be_sent_messages(redis_broker, redis_worker):
    # Given that I have a database
    database = {}

    # And an actor that can write data to that database
    @dramatiq.actor()
    def put(key, value):
        database[key] = value

    # If I send that actor many async messages
    for i in range(100):
        assert put.send("key-%s" % i, i)

    # And I give the workers time to process the messages
    redis_broker.join(put.queue_name)
    redis_worker.join()

    # I expect the database to be populated
    assert len(database) == 100


def test_redis_actors_retry_with_backoff_on_failure(redis_broker, redis_worker):
    # Given that I have a database
    failure_time, success_time = None, None

    # And an actor that fails the first time it's called
    @dramatiq.actor(min_backoff=1000, max_backoff=5000, max_retries=1)
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
    redis_broker.join(do_work.queue_name)
    redis_worker.join()

    # I expect backoff time to have passed between success and failure
    # + the worker idle timeout as padding in case the worker is long polling
    assert 500 <= success_time - failure_time <= 2500 + redis_worker.worker_timeout


def test_redis_actors_can_retry_multiple_times(redis_broker, redis_worker):
    # Given that I have a database
    attempts = []

    # And an actor that fails 3 times then succeeds
    @dramatiq.actor(min_backoff=1000, max_backoff=1000)
    def do_work():
        attempts.append(1)
        if sum(attempts) < 4:
            raise RuntimeError("Failure #%s" % sum(attempts))

    # If I send it a message
    do_work.send()

    # Then join on the queue
    redis_broker.join(do_work.queue_name)
    redis_worker.join()

    # I expect it to have been attempted 4 times
    assert sum(attempts) == 4


def test_redis_actors_can_have_their_messages_delayed(redis_broker, redis_worker):
    # Given that I have a database
    start_time, run_time = current_millis(), None

    # And an actor that records the time it ran
    @dramatiq.actor()
    def record():
        nonlocal run_time
        run_time = current_millis()

    # If I send it a delayed message
    record.send_with_options(delay=1000)

    # Then join on the queue
    redis_broker.join(record.queue_name)
    redis_worker.join()

    # I expect that message to have been processed at least delayed milliseconds later
    assert run_time - start_time >= 1000


def test_redis_actors_can_delay_messages_independent_of_each_other(redis_broker):
    # Given that I have a database
    results = []

    # And an actor that appends a number to the database
    @dramatiq.actor()
    def append(x):
        results.append(x)

    # When I pause the worker
    with worker(redis_broker, worker_timeout=100, worker_threads=1) as redis_worker:
        redis_worker.pause()

        # And I send it a delayed message
        append.send_with_options(args=(1,), delay=2000)

        # And then another delayed message with a smaller delay
        append.send_with_options(args=(2,), delay=1000)

        # Then resume the worker and join on the queue
        redis_worker.resume()
        redis_broker.join(append.queue_name)
        redis_worker.join()

        # I expect the latter message to have been run first
        assert results == [2, 1]


def test_redis_unacked_messages_can_be_requeued(redis_broker):
    # Given that I have a Redis broker
    queue_name = "some-queue"
    redis_broker.declare_queue(queue_name)

    num_messages = LUA_MAX_UNPACK_SIZE * 2
    # The lua max stack size is 8000, so try to work with double that
    message_ids = [("message-%s" % i).encode() for i in range(num_messages)]

    # If I enqueue many messages
    for message_id in message_ids:
        redis_broker.do_enqueue(queue_name, message_id, b"message-data")

    # And then fetch them
    for _ in message_ids:
        redis_broker.do_fetch(queue_name, 1)

    # Then both must be in the acks set
    ack_group = "dramatiq:__acks__.%s.%s" % (redis_broker.broker_id, queue_name)
    unacked = redis_broker.client.smembers(ack_group)
    assert sorted(unacked) == sorted(message_ids)

    # When I close that broker and open another and dispatch a command
    redis_broker.broker_id = "some-other-id"
    redis_broker.heartbeat_timeout = 0
    redis_broker.maintenance_chance = MAINTENANCE_SCALE
    redis_broker.do_qsize(queue_name)

    # Then all messages should be requeued
    ack_group = "dramatiq:__acks__.%s.%s" % (redis_broker.broker_id, queue_name)
    unacked = redis_broker.client.smembers(ack_group)
    assert not unacked

    queued = redis_broker.client.lrange("dramatiq:%s" % queue_name, 0, num_messages)
    assert set(message_ids) == set(queued)


def test_redis_messages_can_be_dead_lettered(redis_broker, redis_worker):
    # Given that I have an actor that always fails
    @dramatiq.actor(max_retries=0)
    def do_work():
        raise RuntimeError("failed")

    # If I send it a message
    do_work.send()

    # And then join on its queue
    redis_broker.join(do_work.queue_name)
    redis_worker.join()

    # I expect it to end up in the dead letter queue
    dead_queue_name = "dramatiq:%s" % xq_name(do_work.queue_name)
    dead_ids = redis_broker.client.zrangebyscore(dead_queue_name, 0, "+inf")
    assert dead_ids


def test_redis_dead_lettered_messages_are_cleaned_up(redis_broker, redis_worker):
    # Given that I have an actor that always fails
    @dramatiq.actor(max_retries=0)
    def do_work():
        raise RuntimeError("failed")

    # When I send it many messages
    for _ in range(LUA_MAX_UNPACK_SIZE * 2):
        do_work.send()

    # And then join on its queue
    redis_broker.join(do_work.queue_name)
    redis_worker.join()

    # And trigger maintenance
    redis_broker.dead_message_ttl = 0
    redis_broker.maintenance_chance = MAINTENANCE_SCALE
    redis_broker.do_qsize(do_work.queue_name)

    # Then all the messages should be removed from the DLQ.
    dead_queue_name = "dramatiq:%s" % xq_name(do_work.queue_name)
    dead_ids = redis_broker.client.zrangebyscore(dead_queue_name, 0, "+inf")
    assert not dead_ids


def test_redis_messages_belonging_to_missing_actors_are_rejected(redis_broker, redis_worker):
    # Given that I have a broker without actors
    # If I send it a message
    message = Message(
        queue_name="some-queue",
        actor_name="some-actor",
        args=(),
        kwargs={},
        options={},
    )
    redis_broker.declare_queue("some-queue")
    message = redis_broker.enqueue(message)

    # Then join on the queue
    redis_broker.join("some-queue")
    redis_worker.join()

    # I expect the message to end up on the dead letter queue
    dead_queue_name = "dramatiq:%s" % xq_name("some-queue")
    dead_ids = redis_broker.client.zrangebyscore(dead_queue_name, 0, "+inf")
    assert message.options["redis_message_id"].encode("utf-8") in dead_ids


def test_redis_requeues_unhandled_messages_on_shutdown(redis_broker):
    # Given that I have an actor that takes its time
    @dramatiq.actor
    def do_work():
        time.sleep(1)

    # If I send it two messages
    message_1 = do_work.send()
    message_2 = do_work.send()

    # Then start a worker and subsequently shut it down
    with worker(redis_broker, worker_threads=1):
        time.sleep(0.25)

    # I expect it to have processed one of the messages and re-enqueued the other
    messages = redis_broker.client.lrange("dramatiq:%s" % do_work.queue_name, 0, 10)
    if message_1.options["redis_message_id"].encode("utf-8") not in messages:
        assert message_2.options["redis_message_id"].encode("utf-8") in messages

    else:
        assert message_1.options["redis_message_id"].encode("utf-8") in messages


def test_redis_requeues_unhandled_delay_messages_on_shutdown(redis_broker):
    # Given that I have an actor that takes its time
    @dramatiq.actor
    def do_work():
        pass

    # If I send it a delayed message
    message = do_work.send_with_options(delay=10000)

    # Then start a worker and subsequently shut it down
    with worker(redis_broker, worker_threads=1):
        pass

    # I expect it to have re-enqueued the message
    messages = redis_broker.client.lrange("dramatiq:%s" % dq_name(do_work.queue_name), 0, 10)
    assert message.options["redis_message_id"].encode("utf-8") in messages


def test_redis_broker_can_join_with_timeout(redis_broker, redis_worker):
    # Given that I have an actor that takes a long time to run
    @dramatiq.actor
    def do_work():
        time.sleep(1)

    # When I send that actor a message
    do_work.send()

    # And join on its queue with a timeout
    # Then I expect a QueueJoinTimeout to be raised
    with pytest.raises(QueueJoinTimeout):
        redis_broker.join(do_work.queue_name, timeout=500)


def test_redis_broker_can_flush_queues(redis_broker):
    # Given that I have an actor
    @dramatiq.actor
    def do_work():
        pass

    # When I send that actor a message
    do_work.send()

    # And then tell the broker to flush all queues
    redis_broker.flush_all()

    # And then join on the actors's queue
    # Then it should join immediately
    assert redis_broker.join(do_work.queue_name, timeout=200) is None


def test_redis_broker_can_connect_via_url():
    # Given that I have a connection string
    # When I pass that to RedisBroker
    broker = RedisBroker(url="redis://127.0.0.1")

    # Then I should get back a valid connection
    assert broker.client.ping()


def test_redis_broker_can_connect_via_client():
    # Given that I already have redis client in hand
    # When I pass it to RedisBroker
    client = redis.Redis()
    broker = RedisBroker(client=client)

    # Then I should get back a valid connection
    assert broker.client.ping()
    assert broker.client is client


def test_redis_broker_raises_attribute_error_when_given_an_invalid_attribute(redis_broker):
    # Given that I have a Redis broker
    # When I try to access an attribute that doesn't exist
    # Then I should get back an attribute error
    with pytest.raises(AttributeError):
        redis_broker.idontexist


def test_redis_consumer_ack_can_retry_on_connection_error(redis_broker, redis_worker):
    # Given that I have an actor
    @dramatiq.actor
    def do_work():
        pass

    # If I send that actor an async message
    message = do_work.send()
    consumer = redis_worker.consumers[do_work.queue_name].consumer

    do_ack = redis_broker.do_ack

    with mock.patch.object(consumer.broker, "do_ack") as ack_mock:

        def side_effect(queue, msg_id):
            if ack_mock.call_count == 1:
                # On the first try, I expect there to be an outstanding message
                assert consumer.outstanding_message_count == 1
            else:
                # On each subsequent try, there should be 0 messages
                assert consumer.outstanding_message_count == 0

            result = do_ack(queue, msg_id)

            if ack_mock.call_count < 2:
                # Trigger a retry by raising a ConnectionError
                raise ConnectionError(message)

            return result

        ack_mock.side_effect = side_effect

        # And I give the workers time to process the messages
        redis_broker.join(do_work.queue_name)
        redis_worker.join()

        # I expect `do_ack` to have been called at least 2 times
        assert ack_mock.call_count >= 2
        # And I expect there to be no outstanding messages
        assert consumer.outstanding_message_count == 0


def test_redis_consumer_nack_can_retry_on_connection_error(redis_broker, redis_worker):
    # Given that I have an actor
    @dramatiq.actor(max_retries=0)
    def do_work():
        raise RuntimeError

    # If I send that actor an async message
    message = do_work.send()
    consumer = redis_worker.consumers[do_work.queue_name].consumer

    do_nack = redis_broker.do_nack

    with mock.patch.object(consumer.broker, "do_nack") as nack_mock:

        def side_effect(queue, msg_id):
            if nack_mock.call_count == 1:
                # On the first try, I expect there to be an outstanding message
                assert consumer.outstanding_message_count == 1
            else:
                # On each subsequent try, there should be 0 messages
                assert consumer.outstanding_message_count == 0

            result = do_nack(queue, msg_id)

            if nack_mock.call_count < 2:
                # Trigger a retry by raising a ConnectionError
                raise ConnectionError(message)

            return result

        nack_mock.side_effect = side_effect

        # And I give the workers time to process the messages
        redis_broker.join(do_work.queue_name)
        redis_worker.join()

        # I expect `do_nack` to have been called at least 2 times
        assert nack_mock.call_count >= 2
        # And I expect there to be no outstanding messages
        assert consumer.outstanding_message_count == 0


def test_redis_consumer_nack_does_not_raise_on_missing_id(redis_worker):
    """
    Reproduces issue 320, exception when the message id is not found.

    https://github.com/Bogdanp/dramatiq/issues/320

    Before the change would raise:
    redis.exceptions.ResponseError: Error running script (call to f_e9668bc413bd4a2d63c8108b124f5b7df0d01263):
    @user_script:218: @user_script: 218: Lua redis() command arguments must be strings or integers
    """

    # Given that I have an actor
    @dramatiq.actor(max_retries=0)
    def do_work():
        raise RuntimeError

    consumer = redis_worker.consumers[do_work.queue_name].consumer

    # If I send a bogus message to nack, I expect no exception to be raised.
    message = Message(
        queue_name=do_work.queue_name,
        actor_name=do_work.actor_name,
        args=(),
        kwargs={},
        options={"redis_message_id": "XXXXXXXXX"},
    )  # Bogus ID
    consumer.nack(message)


def test_redis_join_race_condition(redis_broker):
    """
    test for issue https://github.com/Bogdanp/dramatiq/issues/480

    this test verifies that do_qsize counts all messages in the queue and delay queue at the same
    time, removing the race condition mentioned in the issue
    """
    called = False
    size = []

    @dramatiq.actor
    def go():
        go_again.send_with_options(delay=1000)
        time.sleep(0.25)
        # go ack + go msg + go_again dq.msg + go_again db.ack
        size.append(redis_broker.do_qsize("default"))
        size.append(redis_broker.do_qsize(dq_name("default")))  # does the same

    @dramatiq.actor
    def go_again():
        nonlocal called
        called = True
        size.append(redis_broker.do_qsize("default"))  # go_again msg + go_again ack
        size.append(redis_broker.do_qsize(dq_name("default")))  # does the same

    with worker(redis_broker, worker_timeout=50, worker_threads=1) as redis_worker:
        go.send()
        redis_broker.join("default")
        redis_worker.join()

    assert called
    assert size == [4, 4, 2, 2]
