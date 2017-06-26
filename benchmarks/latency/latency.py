import argparse
import celery
import dramatiq
import logging
import os
import pylibmc
import random
import sys
import subprocess
import time

from dramatiq.brokers.redis import RedisBroker
from dramatiq.brokers.rabbitmq import RabbitmqBroker

logger = logging.getLogger("example")
counter_key = "latench-bench-counter"
memcache_client = pylibmc.Client(["localhost"], binary=True)
memcache_pool = pylibmc.ThreadMappedPool(memcache_client)
random.seed(1337)

if os.getenv("REDIS") == "1":
    broker = RedisBroker()
    dramatiq.set_broker(broker)
    celery_app = celery.Celery(broker="redis:///")

else:
    broker = RabbitmqBroker()
    dramatiq.set_broker(broker)
    celery_app = celery.Celery(broker="amqp:///")


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


dramatiq_latency_bench = dramatiq.actor(latency_bench)
celery_latency_bench = celery_app.task(name="latency-bench")(latency_bench)


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, help="the number of messages to benchmark with", default=10000)
    parser.add_argument("--use-celery", action="store_true", default=False)
    args = parser.parse_args()
    for _ in range(args.count):
        if args.use_celery:
            celery_latency_bench.delay()
        else:
            dramatiq_latency_bench.send()

    print("Done enqueing messages. Booting workers...")
    with memcache_pool.reserve() as client:
        client.set(counter_key, 0)

        start_time = time.time()
        if args.use_celery:
            proc = subprocess.Popen([
                "celery", "worker",
                "-A", "latency.latency.celery_app",
                "--concurrency", "8"])
        else:
            proc = subprocess.Popen([
                "python", "-m", "dramatiq",
                "latency.latency:broker",
                "--processes", "8",
            ])

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
