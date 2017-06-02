import dramatiq
import logging
import random
import sys

logger = logging.getLogger("example")


@dramatiq.actor(actor_name="add")
def add(x, y):
    logger.info("The sum of %d and %d is %d.", x, y, x + y)


def main(args):
    while True:
        add.send(random.randint(0, 1000), random.randint(0, 1000))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
