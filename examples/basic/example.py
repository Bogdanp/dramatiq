import argparse
import dramatiq
import logging
import random
import sys
import time

from dramatiq.brokers.redis import RedisBroker

logger = logging.getLogger("example")
broker = RedisBroker()
dramatiq.set_broker(broker)


@dramatiq.actor
def add(x, y):
    pass


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("count", type=int, help="the number of messages to enqueue")
    args = parser.parse_args()
    for _ in range(args.count):
        add.send(random.randint(0, 1000), random.randint(0, 1000))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
