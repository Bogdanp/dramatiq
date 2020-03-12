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
        raise e if CI else pytest.skip("No connection to RabbmitMQ server.")


def check_redis(client):
    try:
        client.ping()
    except redis.ConnectionError as e:
        raise e if CI else pytest.skip("No connection to Redis server.")


def check_memcached(client):
    try:
        client.get_stats()
    except pylibmc.SomeErrors as e:
        raise e if CI else pytest.skip("No connection to memcached server.")


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
        args = [sys.executable, "-m", "dramatiq", broker_module]
        proc = subprocess.Popen(args + (extra_args or []), **kwargs)
        return proc

    yield run

    if proc is not None:
        proc.terminate()
        proc.wait()


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
def old_and_new_result_modules():
    import dramatiq.results as old_results
    import dramatiq.results_with_failures as new_results
    import dramatiq.results.backends as old_backends
    import dramatiq.results_with_failures.backends as new_backends
    return {
        "old": (old_results, old_backends),
        "new": (new_results, new_backends)
    }


@pytest.fixture(params=["old", "new"])
def result_modules(request, old_and_new_result_modules):
    return old_and_new_result_modules[request.param]


@pytest.fixture
def memcached_result_backend(result_modules):
    results, res_backends = result_modules
    backend = res_backends.MemcachedBackend(servers=["127.0.0.1"], binary=True)
    with backend.pool.reserve() as client:
        check_memcached(client)
        client.flush_all()
    return backend, results


@pytest.fixture
def redis_result_backend(result_modules):
    results, res_backends = result_modules
    backend = res_backends.RedisBackend()
    check_redis(backend.client)
    backend.client.flushall()
    return backend, results


@pytest.fixture
def stub_result_backend(result_modules):
    results, res_backends = result_modules
    return res_backends.StubBackend(), results


@pytest.fixture
def memcached_result_backend_new():
    import dramatiq.results_with_failures as results
    from dramatiq.results_with_failures.backends import MemcachedBackend
    backend = MemcachedBackend(servers=["127.0.0.1"], binary=True)
    with backend.pool.reserve() as client:
        check_memcached(client)
        client.flush_all()
    return backend, results


@pytest.fixture
def redis_result_backend_new():
    import dramatiq.results_with_failures as results
    from dramatiq.results_with_failures.backends import RedisBackend
    backend = RedisBackend()
    check_redis(backend.client)
    backend.client.flushall()
    return backend, results


@pytest.fixture
def stub_result_backend_new():
    import dramatiq.results_with_failures as results
    from dramatiq.results_with_failures.backends import StubBackend
    return StubBackend(), results


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


@pytest.fixture
def result_backends_new(memcached_result_backend_new, redis_result_backend_new, stub_result_backend_new):
    return {
        "memcached-new": memcached_result_backend_new,
        "redis-new": redis_result_backend_new,
        "stub-new": stub_result_backend_new,
    }


@pytest.fixture(params=["memcached-new", "redis-new", "stub-new"])
def result_backend_new(request, result_backends_new):
    return result_backends_new[request.param]
