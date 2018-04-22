import os
import random
import sys
import time

import dramatiq

if os.getenv("REDIS") == "1":
    from dramatiq.brokers.redis import RedisBroker
    broker = RedisBroker()
    dramatiq.set_broker(broker)


def fib(n):
    x, y = 1, 1
    while n > 2:
        x, y = x + y, x
        n -= 1
    return x


@dramatiq.actor(time_limit=86_400_000, max_retries=0)
def long_running(duration):
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        long_running.logger.info("%d seconds remaining.", deadline - time.monotonic())

        n = random.randint(1_000, 1_000_000)
        long_running.logger.debug("Computing fib(%d).", n)

        fib(n)
        long_running.logger.debug("Computed fib(%d).", n)

        sleep = random.randint(1, 30)
        long_running.logger.debug("Sleeping for %d seconds...", sleep)
        time.sleep(sleep)


def main(args):
    for _ in range(1_000):
        long_running.send(random.randint(3_600, 14_400))
        time.sleep(random.randint(60, 3600))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
