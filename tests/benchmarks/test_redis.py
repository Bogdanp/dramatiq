import dramatiq
import logging


def test_redis_process_10k_messages(benchmark, redis_broker):
    @dramatiq.actor
    def throughput():
        pass

    # Given that I've loaded 10k messages into RabbitMQ
    def load_messages():
        for _ in range(10000):
            throughput.send()

    # I expect processing those messages to be consistently fast
    def process_messages():
        worker = dramatiq.Worker(redis_broker)
        worker.start()
        redis_broker.join(throughput.queue_name)
        worker.stop()

    logging.getLogger().setLevel(logging.INFO)
    benchmark.pedantic(process_messages, setup=load_messages)
    logging.getLogger().setLevel(logging.DEBUG)
