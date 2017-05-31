import dramatiq
import logging
import random
import sys
import time


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(threadName)s] [%(name)s] [%(levelname)s] %(message)s",
)


@dramatiq.actor
def add(x, y):
    print(x + y)


def main(args):
    while True:
        add.send(random.randint(0, 1000), random.randint(0, 1000))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
