import dramatiq
import logging
import pytest
import random
import subprocess
import uuid

from dramatiq import Worker
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from dramatiq.brokers.redis import RedisBroker
from dramatiq.brokers.stub import StubBroker
from dramatiq.common import dq_name, xq_name
from dramatiq.rate_limits.backends import MemcachedBackend, RedisBackend


logfmt = "[%(asctime)s] [%(threadName)s] [%(name)s] [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.DEBUG, format=logfmt)
logging.getLogger("pika").setLevel(logging.WARN)

random.seed(1337)


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
    broker.client.flushall()
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
def urlrabbitmq_worker(urlrabbitmq_broker):
    worker = Worker(urlrabbitmq_broker)
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
    queue_name = "rabbit-queue-%s" % uuid.uuid4()
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

    def run(broker_module, *, extra_args=[], **kwargs):
        nonlocal proc
        args = ["python", "-m", "dramatiq", broker_module]
        proc = subprocess.Popen(args + extra_args, **kwargs)
        return proc

    yield run

    if proc is not None:
        proc.terminate()
        proc.wait()


@pytest.fixture
def memcached_rate_limiter_backend():
    backend = MemcachedBackend(servers=["127.0.0.1"], binary=True)
    with backend.pool.reserve() as client:
        client.flush_all()
    return backend


@pytest.fixture
def redis_rate_limiter_backend():
    backend = RedisBackend()
    backend.client.flushall()
    return backend


@pytest.fixture
def rate_limiter_backends(memcached_rate_limiter_backend, redis_rate_limiter_backend):
    return {
        "memcached": memcached_rate_limiter_backend,
        "redis": redis_rate_limiter_backend,
    }
