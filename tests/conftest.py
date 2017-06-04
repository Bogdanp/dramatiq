import dramatiq
import logging
import pytest
import uuid

from dramatiq import Worker
from dramatiq.brokers import RabbitmqBroker, StubBroker


logfmt = "[%(asctime)s] [%(threadName)s] [%(name)s] [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.DEBUG, format=logfmt)
logging.getLogger("pika").setLevel(logging.WARN)


@pytest.fixture()
def stub_broker():
    broker = StubBroker()
    dramatiq.set_broker(broker)
    return broker


@pytest.fixture()
def rabbitmq_broker():
    broker = RabbitmqBroker()
    dramatiq.set_broker(broker)
    return broker


@pytest.fixture()
def stub_worker(stub_broker):
    worker = Worker(stub_broker, worker_timeout=100)
    worker.start()
    yield worker
    worker.stop()


@pytest.fixture()
def rabbitmq_worker(rabbitmq_broker):
    worker = Worker(rabbitmq_broker)
    worker.start()
    yield worker
    worker.stop()


@pytest.fixture()
def rabbitmq_random_queue(rabbitmq_broker):
    queue_name = f"rabbit-queue-{uuid.uuid4()}"
    yield queue_name
    rabbitmq_broker.channel.queue_delete(queue_name)
