import dramatiq
import time


def current_millis():
    return int(time.time() * 1000)


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
