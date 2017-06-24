import dramatiq

from dramatiq.brokers.rabbitmq import RabbitmqBroker

broker = RabbitmqBroker()


@dramatiq.actor(queue_name="benchmark-throughput", broker=broker)
def throughput():
    pass


@dramatiq.actor(queue_name="benchmark-sum", broker=broker)
def sum_all(xs):
    sum(xs)


def test_rabbitmq_process_100k_messages_with_cli(benchmark, info_logging, start_cli):
    # Given that I've loaded 100k messages into RabbitMQ
    def setup():
        # The connection error tests have the side-effect of
        # disconnecting this broker so we need to force it to
        # reconnect.
        del broker.channel
        del broker.connection

        for _ in range(100000):
            throughput.send()

        start_cli("tests.benchmarks.test_rabbitmq_cli:broker")

    # I expect processing those messages with the CLI to be consistently fast
    benchmark.pedantic(broker.join, args=(throughput.queue_name,), setup=setup)


def test_rabbitmq_process_100k_sums_with_cli(benchmark, info_logging, start_cli):
    # Given that I've loaded 100k messages into RabbitMQ
    def setup():
        # The connection error tests have the side-effect of
        # disconnecting this broker so we need to force it to
        # reconnect.
        del broker.channel
        del broker.connection

        numbers = [i for i in range(100)]
        for _ in range(100000):
            sum_all.send(numbers)

        start_cli("tests.benchmarks.test_rabbitmq_cli:broker")

    # I expect processing those messages with the CLI to be consistently fast
    benchmark.pedantic(broker.join, args=(sum_all.queue_name,), setup=setup)
