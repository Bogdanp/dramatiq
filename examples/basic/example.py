import argparse
import os
import random
import sys

import remoulade

if os.getenv("REDIS") == "1":
    from remoulade.brokers.redis import RedisBroker
    broker = RedisBroker()
    remoulade.set_broker(broker)


@remoulade.actor
def add(x, y):
    add.logger.info("The sum of %d and %d is %d.", x, y, x + y)


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("count", type=int, help="the number of messages to enqueue")
    args = parser.parse_args()
    for _ in range(args.count):
        add.send(random.randint(0, 1000), random.randint(0, 1000))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
