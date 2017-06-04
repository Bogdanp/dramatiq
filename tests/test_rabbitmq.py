import dramatiq


def test_actors_can_be_sent_messages_over_rabbitmq(rabbitmq_broker, rabbitmq_random_queue, rabbitmq_worker):
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

    # I expect the database to be populated
    assert len(database) == 100
