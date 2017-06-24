import dramatiq

from dramatiq.brokers.redis import RedisBroker

broker = RedisBroker()


@dramatiq.actor(queue_name="benchmark-throughput", broker=broker)
def throughput():
    pass


@dramatiq.actor(queue_name="benchmark-sum", broker=broker)
def sum_all(xs):
    sum(xs)


def test_redis_process_100k_messages_with_cli(benchmark, info_logging, start_cli):
    # Given that I've loaded 100k messages into Redis
    def setup():
        for _ in range(100_000):
            throughput.send()

        start_cli("tests.benchmarks.test_redis_cli:broker")

    # I expect processing those messages with the CLI to be consistently fast
    benchmark.pedantic(broker.join, args=(throughput.queue_name,), setup=setup)


def test_redis_process_100k_sums_with_cli(benchmark, info_logging, start_cli):
    # Given that I've loaded 100k messages into Redis
    def setup():
        numbers = [i for i in range(100)]
        for _ in range(100_000):
            sum_all.send(numbers)

        start_cli("tests.benchmarks.test_redis_cli:broker")

    # I expect processing those messages with the CLI to be consistently fast
    benchmark.pedantic(broker.join, args=(sum_all.queue_name,), setup=setup)
