import dramatiq
import dramatiq.brokers
import logging
import subprocess

broker = dramatiq.brokers.RabbitmqBroker()


@dramatiq.actor(queue_name="throughput", broker=broker)
def throughput():
    pass


def test_rabbitmq_process_100k_messages_with_cli(benchmark):
    # Given that I've loaded 100k messages into RabbitMQ
    def load_messages():
        for _ in range(100000):
            throughput.send()

    # I expect processing those messages with the CLI to be consistently fast
    def process_messages():
        proc = subprocess.Popen(["python", "-m", "dramatiq", "tests.benchmarks.test_cli:broker"])
        broker.join(throughput.queue_name)
        proc.terminate()
        proc.wait()

    logging.getLogger().setLevel(logging.INFO)
    benchmark.pedantic(process_messages, setup=load_messages)
    logging.getLogger().setLevel(logging.DEBUG)
