import argparse
import dramatiq
import logging
import random
import sys

logger = logging.getLogger("example")


@dramatiq.actor
def add(x, y):
    if random.randint(1, 100) == 1:
        raise RuntimeError("an exception")
    logger.info("The sum of %d and %d is %d.", x, y, x + y)


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("count", type=int, help="the number of messages to enqueue")
    args = parser.parse_args()
    for _ in range(args.count):
        add.send(random.randint(0, 1000), random.randint(0, 1000))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
