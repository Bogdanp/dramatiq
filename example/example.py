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


def worker():
    try:
        worker = dramatiq.Worker(dramatiq.get_broker())
        worker.start()
        while True:
            time.sleep(1)
        return 0
    except KeyboardInterrupt:
        worker.stop()
        return 0


def sender():
    while True:
        add.send(random.randint(0, 1000), random.randint(0, 1000))


def main(args):
    if len(args) != 2 or args[1] not in ("worker", "sender"):
        print("usage: python example.py [worker|sender]")
        return 1

    if args[1] == "worker":
        return worker()
    return sender()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
