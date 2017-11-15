import dramatiq
import pytest
import time

from dramatiq import Message, Worker
from dramatiq.common import current_millis, dq_name, xq_name


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

    # I expect backoff time to have passed between sucess and failure
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


def test_redis_actors_can_delay_messages_independent_of_each_other(redis_broker, redis_worker):
    # Given that I have a database
    results = []

    # And an actor that appends a number to the database
    @dramatiq.actor()
    def append(x):
        results.append(x)

    # If I send it a delayed message
    append.send_with_options(args=(1,), delay=2000)

    # And then another delayed message with a smaller delay
    append.send_with_options(args=(2,), delay=1000)

    # Then join on the queue
    redis_broker.join(append.queue_name)
    redis_worker.join()

    # I expect the latter message to have been run first
    assert results == [2, 1]


def test_redis_unacked_messages_can_be_requeued(redis_broker):
    # Given that I have a Redis broker
    queue_name = "some-queue"
    redis_broker.declare_queue(queue_name)

    # If I enqueue two messages
    message_ids = [b"message-1", b"message-2"]
    for message_id in message_ids:
        redis_broker._enqueue(queue_name, message_id, b"message-data")

    # And then fetch them one second apart
    redis_broker._fetch(queue_name, 1)
    time.sleep(1)
    redis_broker._fetch(queue_name, 1)

    # I expect both to be in the acks set
    unacked = redis_broker.client.zrangebyscore("dramatiq:%s.acks" % queue_name, 0, "+inf")
    assert sorted(unacked) == sorted(message_ids)

    # If I then set the requeue deadline to 1 second and run a requeue
    redis_broker.requeue_deadline = 1000
    redis_broker._requeue()

    # I expect only the first message to have been moved
    unacked = redis_broker.client.zrangebyscore("dramatiq:%s.acks" % queue_name, 0, "+inf")
    queued = redis_broker.client.lrange("dramatiq:%s" % queue_name, 0, 1)
    assert unacked == message_ids[1:]
    assert queued == message_ids[:1]


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

    # If I send it a message
    do_work.send()

    # And then join on its queue
    redis_broker.join(do_work.queue_name)
    redis_worker.join()

    # I expect running the cleanup script to remove it
    redis_broker.dead_message_ttl = 0
    redis_broker._cleanup()
    dead_queue_name = "dramatiq:%s" % xq_name(do_work.queue_name)
    dead_ids = redis_broker.client.zrangebyscore(dead_queue_name, 0, "+inf")
    assert not dead_ids


def test_redis_messages_belonging_to_missing_actors_are_rejected(redis_broker, redis_worker):
    # Given that I have a broker without actors
    # If I send it a message
    message = Message(
        queue_name="some-queue",
        actor_name="some-actor",
        args=(), kwargs={},
        options={},
    )
    redis_broker.declare_queue("some-queue")
    message = redis_broker.enqueue(message)

    # Then join on the queue
    redis_broker.join("some-queue")
    redis_worker.join()

    # I expect the message to end up on the dead letter queue
    dead_queue_name = "dramatiq:%s" % xq_name('some-queue')
    dead_ids = redis_broker.client.zrangebyscore(dead_queue_name, 0, "+inf")
    assert message.options["redis_message_id"].encode("utf-8") in dead_ids


def test_redis_raises_an_exception_when_delaying_messages_for_too_long(redis_broker):
    # Given that I have an actor
    @dramatiq.actor
    def do_nothing():
        pass

    # If I try to send it a delayed message farther than 7 days into the future
    # I expect it to raise a value error
    with pytest.raises(ValueError):
        do_nothing.send_with_options(delay=7 * 86400 * 1000 + 1)


def test_redis_requeues_unhandled_messages_on_shutdown(redis_broker):
    # Given that I have an actor that takes its time
    @dramatiq.actor
    def do_work():
        time.sleep(1)

    # If I send it two messages
    message_1 = do_work.send()
    message_2 = do_work.send()

    # Then start a worker and subsequently shut it down
    worker = Worker(redis_broker, worker_threads=1)
    worker.start()
    time.sleep(0.25)
    worker.stop()

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
    worker = Worker(redis_broker, worker_threads=1)
    worker.start()
    worker.stop()

    # I expect it to have re-enqueued the message
    messages = redis_broker.client.lrange("dramatiq:%s" % dq_name(do_work.queue_name), 0, 10)
    assert message.options["redis_message_id"].encode("utf-8") in messages
