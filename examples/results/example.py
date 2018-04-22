import argparse
import random
import sys
import time

import dramatiq
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from dramatiq.encoder import PickleEncoder
from dramatiq.results import Results
from dramatiq.results.backends import RedisBackend

result_backend = RedisBackend(encoder=PickleEncoder())
broker = RabbitmqBroker()
broker.add_middleware(Results(backend=result_backend))
dramatiq.set_broker(broker)


@dramatiq.actor(store_results=True)
def sleep_then_add(t, x, y):
    time.sleep(t)
    return x + y


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("count", type=int, help="the number of messages to enqueue")
    args = parser.parse_args()

    messages = []
    for _ in range(args.count):
        messages.append(sleep_then_add.send(
            random.randint(1, 5),
            random.randint(0, 1000),
            random.randint(0, 1000)
        ))

    for message in messages:
        print(message.get_result(block=True))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
