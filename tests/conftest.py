import dramatiq
import logging
import pytest

from dramatiq import Worker
from dramatiq.brokers import StubBroker


logging.basicConfig(level=logging.DEBUG)


@pytest.fixture()
def stub_broker():
    broker = StubBroker()
    dramatiq.set_broker(broker)
    return broker


@pytest.fixture()
def stub_worker(stub_broker):
    worker = Worker(stub_broker, get_timeout=0.1)
    yield worker
    worker.stop()
