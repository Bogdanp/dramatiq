import dramatiq
import logging
import pytest


@pytest.mark.benchmark(group="rabbitmq-10k")
def test_rabbitmq_process_10k_messages(benchmark, rabbitmq_broker, rabbitmq_random_queue):
    @dramatiq.actor(queue_name=rabbitmq_random_queue)
    def throughput():
        pass

    # Given that I've loaded 10k messages into RabbitMQ
    def load_messages():
        for _ in range(10000):
            throughput.send()

    # I expect processing those messages to be consistently fast
    def process_messages():
        worker = dramatiq.Worker(rabbitmq_broker)
        worker.start()
        rabbitmq_broker.join(rabbitmq_random_queue)
        worker.stop()

    logging.getLogger().setLevel(logging.INFO)
    benchmark.pedantic(process_messages, setup=load_messages)
    logging.getLogger().setLevel(logging.DEBUG)
