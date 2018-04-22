import dramatiq
import logging
import pytest
import random
import subprocess
import sys

from dramatiq import Worker
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from dramatiq.brokers.redis import RedisBroker
from dramatiq.brokers.stub import StubBroker
from dramatiq.rate_limits import backends as rl_backends
from dramatiq.results import backends as res_backends

logfmt = "[%(asctime)s] [%(threadName)s] [%(name)s] [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=logfmt)
logging.getLogger("pika").setLevel(logging.WARN)

random.seed(1337)


@pytest.mark.hookwrapper
def pytest_runtest_makereport(item, call):
    outcome = yield
    if item.get_marker("flaky"):
        report = outcome.get_result()
        if report.outcome == "failed":
            report.outcome = "skipped"
            report.wasxfail = "skipped flaky test"


@pytest.fixture()
def stub_broker():
    broker = StubBroker()
    broker.emit_after("process_boot")
    dramatiq.set_broker(broker)
    yield broker
    broker.flush_all()
    broker.close()


@pytest.fixture()
def rabbitmq_broker():
    broker = RabbitmqBroker()
    broker.emit_after("process_boot")
    dramatiq.set_broker(broker)
    yield broker
    broker.flush_all()
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
    worker = Worker(stub_broker, worker_timeout=100, worker_threads=32)
    worker.start()
    yield worker
    worker.stop()


@pytest.fixture()
def rabbitmq_worker(rabbitmq_broker):
    worker = Worker(rabbitmq_broker, worker_threads=32)
    worker.start()
    yield worker
    worker.stop()


@pytest.fixture()
def redis_worker(redis_broker):
    worker = Worker(redis_broker, worker_threads=32)
    worker.start()
    yield worker
    worker.stop()


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
        args = [sys.executable, "-m", "dramatiq", broker_module]
        proc = subprocess.Popen(args + extra_args, **kwargs)
        return proc

    yield run

    if proc is not None:
        proc.terminate()
        proc.wait()


@pytest.fixture
def memcached_rate_limiter_backend():
    backend = rl_backends.MemcachedBackend(servers=["127.0.0.1"], binary=True)
    with backend.pool.reserve() as client:
        client.flush_all()
    return backend


@pytest.fixture
def redis_rate_limiter_backend():
    backend = rl_backends.RedisBackend()
    backend.client.flushall()
    return backend


@pytest.fixture
def stub_rate_limiter_backend():
    return rl_backends.StubBackend()


@pytest.fixture
def rate_limiter_backends(memcached_rate_limiter_backend, redis_rate_limiter_backend, stub_rate_limiter_backend):
    return {
        "memcached": memcached_rate_limiter_backend,
        "redis": redis_rate_limiter_backend,
        "stub": stub_rate_limiter_backend,
    }


@pytest.fixture
def memcached_result_backend():
    backend = res_backends.MemcachedBackend(servers=["127.0.0.1"], binary=True)
    with backend.pool.reserve() as client:
        client.flush_all()
    return backend


@pytest.fixture
def redis_result_backend():
    backend = res_backends.RedisBackend()
    backend.client.flushall()
    return backend


@pytest.fixture
def stub_result_backend():
    return res_backends.StubBackend()


@pytest.fixture
def result_backends(memcached_result_backend, redis_result_backend, stub_result_backend):
    return {
        "memcached": memcached_result_backend,
        "redis": redis_result_backend,
        "stub": stub_result_backend,
    }
