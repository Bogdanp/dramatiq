import dramatiq

from dramatiq import Message


def test_actors_can_be_defined(stub_broker):
    # Given that I've decorated a function with @actor
    @dramatiq.actor
    def add(x, y):
        return x + y

    # I expect that function to become an instance of Actor
    assert isinstance(add, dramatiq.Actor)


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
