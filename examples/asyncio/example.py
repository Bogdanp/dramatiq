import argparse
import asyncio
import os
import random
import sys

import dramatiq
from dramatiq.middleware.asyncio import AsyncIO

if os.getenv("REDIS") == "1":
    from dramatiq.brokers.redis import RedisBroker
    broker = RedisBroker()
    dramatiq.set_broker(broker)

dramatiq.get_broker().add_middleware(AsyncIO())


@dramatiq.actor
async def add(x, y):
    add.logger.info("About to compute the sum of %d and %d.", x, y)
    await asyncio.sleep(random.uniform(0.1, 0.3))
    add.logger.info("The sum of %d and %d is %d.", x, y, x + y)


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("count", type=int, help="the number of messages to enqueue")
    args = parser.parse_args()
    for _ in range(args.count):
        add.send(random.randint(0, 1000), random.randint(0, 1000))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
