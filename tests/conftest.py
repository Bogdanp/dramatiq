import dramatiq
import logging
import pytest

from dramatiq import Worker
from dramatiq.brokers import RabbitmqBroker, StubBroker


logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] [%(threadName)s] [%(name)s] [%(levelname)s] %(message)s",
)


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
    worker = Worker(stub_broker, wait_timeout=0.1)
    worker.start()
    yield worker
    worker.stop()


@pytest.fixture()
def rabbitmq_worker(rabbitmq_broker):
    worker = Worker(rabbitmq_broker)
    worker.start()
    yield worker
    worker.stop()
