import argparse
import sys

import requests

import remoulade
from remoulade import group
from remoulade.brokers.rabbitmq import RabbitmqBroker
from remoulade.encoder import PickleEncoder
from remoulade.results import Results
from remoulade.results.backends import RedisBackend

encoder = PickleEncoder()
backend = RedisBackend(encoder=encoder)
broker = RabbitmqBroker(host="127.0.0.1")
broker.add_middleware(Results(backend=backend))
remoulade.set_broker(broker)
remoulade.set_encoder(encoder)


@remoulade.actor
def request(uri):
    return requests.get(uri)


@remoulade.actor(store_results=True)
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
