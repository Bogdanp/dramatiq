import dramatiq
import logging
import pytest
import subprocess
import uuid

from dramatiq import Worker
from dramatiq.brokers import StubBroker
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from dramatiq.brokers.redis import RedisBroker
from dramatiq.common import dq_name, xq_name


logfmt = "[%(asctime)s] [%(threadName)s] [%(name)s] [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.DEBUG, format=logfmt)
logging.getLogger("pika").setLevel(logging.WARN)


@pytest.fixture()
def stub_broker():
    broker = StubBroker()
    broker.emit_after("process_boot")
    dramatiq.set_broker(broker)
    yield broker
    broker.close()


@pytest.fixture()
def rabbitmq_broker():
    broker = RabbitmqBroker()
    broker.emit_after("process_boot")
    dramatiq.set_broker(broker)
    yield broker
    broker.close()


@pytest.fixture()
def redis_broker():
    broker = RedisBroker()
    broker.client.flushall()
    broker.emit_after("process_boot")
    dramatiq.set_broker(broker)
    yield broker
    broker.close()


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
def redis_worker(redis_broker):
    worker = Worker(redis_broker)
    worker.start()
    yield worker
    worker.stop()


@pytest.fixture()
def rabbitmq_random_queue(rabbitmq_broker):
    queue_name = f"rabbit-queue-{uuid.uuid4()}"
    yield queue_name
    rabbitmq_broker.channel.queue_delete(queue_name)
    rabbitmq_broker.channel.queue_delete(dq_name(queue_name))
    rabbitmq_broker.channel.queue_delete(xq_name(queue_name))


@pytest.fixture
def info_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    yield
    logger.setLevel(logging.DEBUG)


@pytest.fixture
def start_cli():
    proc = None

    def run(broker_module):
        nonlocal proc
        proc = subprocess.Popen(["python", "-m", "dramatiq", broker_module])

    yield run

    if proc is not None:
        proc.terminate()
        proc.wait()
