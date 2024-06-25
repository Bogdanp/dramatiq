import logging
import os
import random
import subprocess
import sys

import pylibmc
import pytest
import redis

import dramatiq
from dramatiq import Worker
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from dramatiq.brokers.redis import RedisBroker
from dramatiq.brokers.stub import StubBroker
from dramatiq.rate_limits import backends as rl_backends
from dramatiq.results import backends as res_backends

from .common import RABBITMQ_CREDENTIALS

logfmt = "[%(asctime)s] [%(threadName)s] [%(name)s] [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=logfmt)
logging.getLogger("pika").setLevel(logging.WARN)

random.seed(1337)

CI = os.getenv("GITHUB_ACTION") or \
    os.getenv("APPVEYOR") == "true"


def check_rabbitmq(broker):
    try:
        broker.connection
    except Exception as e:
        raise e if CI else pytest.skip("No connection to RabbmitMQ server.") from None


def check_redis(client):
    try:
        client.ping()
    except redis.ConnectionError as e:
        raise e if CI else pytest.skip("No connection to Redis server.") from None


def check_memcached(client):
    try:
        client.get_stats()
    except pylibmc.SomeErrors as e:
        raise e if CI else pytest.skip("No connection to memcached server.") from None


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
    broker = RabbitmqBroker(
        host="127.0.0.1",
        max_priority=10,
        credentials=RABBITMQ_CREDENTIALS,
    )
    check_rabbitmq(broker)
    broker.emit_after("process_boot")
    dramatiq.set_broker(broker)
    yield broker
    broker.flush_all()
    broker.close()


@pytest.fixture()
def redis_broker():
    broker = RedisBroker()
    check_redis(broker.client)
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

    def run(broker_module, *, extra_args=None, **kwargs):
        nonlocal proc
        kwargs.setdefault("bufsize", 0)
        args = [sys.executable, "-m", "dramatiq", broker_module]
        proc = subprocess.Popen(args + (extra_args or []), **kwargs)
        return proc

    yield run

    if proc is not None:
        proc.terminate()
        proc.wait()
        if proc.stdout is not None:
            proc.stdout.close()


@pytest.fixture
def memcached_rate_limiter_backend():
    backend = rl_backends.MemcachedBackend(servers=["127.0.0.1"], binary=True)
    with backend.pool.reserve() as client:
        check_memcached(client)
        client.flush_all()
    return backend


@pytest.fixture
def redis_rate_limiter_backend():
    backend = rl_backends.RedisBackend()
    check_redis(backend.client)
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


@pytest.fixture(params=["memcached", "redis", "stub"])
def rate_limiter_backend(request, rate_limiter_backends):
    return rate_limiter_backends[request.param]


@pytest.fixture
def memcached_result_backend():
    backend = res_backends.MemcachedBackend(servers=["127.0.0.1"], binary=True)
    with backend.pool.reserve() as client:
        check_memcached(client)
        client.flush_all()
    return backend


@pytest.fixture
def redis_result_backend():
    backend = res_backends.RedisBackend()
    check_redis(backend.client)
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


@pytest.fixture(params=["memcached", "redis", "stub"])
def result_backend(request, result_backends):
    return result_backends[request.param]
