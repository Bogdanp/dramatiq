import argparse
import logging
import os
import random
import subprocess
import sys
import time

import celery
import pylibmc

import dramatiq
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from dramatiq.brokers.redis import RedisBroker

logger = logging.getLogger("example")
counter_key = "latench-bench-counter"
memcache_client = pylibmc.Client(["localhost"], binary=True)
memcache_pool = pylibmc.ClientPool(memcache_client, 8)
random.seed(1337)

if os.getenv("REDIS") == "1":
    broker = RedisBroker()
    dramatiq.set_broker(broker)
    celery_app = celery.Celery(broker="redis:///")

else:
    broker = RabbitmqBroker(host="127.0.0.1")
    dramatiq.set_broker(broker)
    celery_app = celery.Celery(broker="amqp:///")


def fib_bench(n):
    p, q = 0, 1
    while n > 0:
        p, q = q, p + q
        n -= 1

    with memcache_pool.reserve() as client:
        client.incr(counter_key)

    return p


def latency_bench():
    p = random.randint(1, 100)
    if p == 1:
        duration = 10
    elif p <= 30:
        duration = 5
    elif p <= 50:
        duration = 3
    else:
        duration = 1

    time.sleep(duration)
    with memcache_pool.reserve() as client:
        client.incr(counter_key)


dramatiq_fib_bench = dramatiq.actor(fib_bench)
dramatiq_latency_bench = dramatiq.actor(latency_bench)

celery_fib_bench = celery_app.task(name="fib-bench", acks_late=True)(fib_bench)
celery_latency_bench = celery_app.task(name="latency-bench", acks_late=True)(latency_bench)


def benchmark_arg(value):
    benchmarks = ("fib", "latency")
    if value not in benchmarks:
        raise argparse.ArgumentTypeError(f"benchmark must be one of {benchmarks!r}")
    return value


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--benchmark", help="the benchmark to run",
        type=benchmark_arg, default="latency",
    )
    parser.add_argument(
        "--count", help="the number of messages to benchmark with",
        type=int, default=10000,
    )
    parser.add_argument(
        "--use-green-threads", help="run workers with green threads rather than system threads",
        action="store_true", default=False,
    )
    parser.add_argument(
        "--use-celery", help="run the benchmark under Celery",
        action="store_true", default=False,
    )
    return parser.parse_args()


def main(args):
    args = parse_args()
    for _ in range(args.count):
        if args.use_celery:
            if args.benchmark == "latency":
                celery_latency_bench.delay()

            elif args.benchmark == "fib":
                celery_fib_bench.delay(random.randint(1, 200))

        else:
            if args.benchmark == "latency":
                dramatiq_latency_bench.send()

            elif args.benchmark == "fib":
                dramatiq_fib_bench.send(random.randint(1, 200))

    print("Done enqueing messages. Booting workers...")
    with memcache_pool.reserve() as client:
        client.set(counter_key, 0)

        start_time = time.time()
        if args.use_celery:
            subprocess_args = ["celery", "worker", "-A", "bench.celery_app"]
            if args.use_green_threads:
                subprocess_args.extend(["-P", "eventlet", "-c", "2000"])
            else:
                subprocess_args.extend(["-c", "8"])

        else:
            if args.use_green_threads:
                subprocess_args = ["dramatiq-gevent", "bench", "-p", "8", "-t", "250"]

            else:
                subprocess_args = ["dramatiq", "bench", "-p", "8"]

        proc = subprocess.Popen(subprocess_args)
        processed = 0
        while processed < args.count:
            processed = client.get(counter_key)
            print(f"{processed}/{args.count} messages processed\r", end="")
            time.sleep(0.1)

        duration = time.time() - start_time
        proc.terminate()
        proc.wait()

    print(f"Took {duration} seconds to process {args.count} messages.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
