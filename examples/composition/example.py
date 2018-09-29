import argparse
import sys

import requests

import dramatiq
from dramatiq import group
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from dramatiq.encoder import PickleEncoder
from dramatiq.results import Results
from dramatiq.results.backends import RedisBackend

encoder = PickleEncoder()
backend = RedisBackend(encoder=encoder)
broker = RabbitmqBroker(host="127.0.0.1")
broker.add_middleware(Results(backend=backend))
dramatiq.set_broker(broker)
dramatiq.set_encoder(encoder)


@dramatiq.actor
def request(uri):
    return requests.get(uri)


@dramatiq.actor(store_results=True)
def count_words(response):
    return len(response.text.split(" "))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("uri", nargs="+", help="A website URI.")

    arguments = parser.parse_args()
    jobs = group(request.message(uri) | count_words.message() for uri in arguments.uri).run()
    for uri, count in zip(arguments.uri, jobs.get_results(block=True)):
        print(f" * {uri} has {count} words")

    return 0


if __name__ == "__main__":
    sys.exit(main())
