import dramatiq
import logging
import os
import sys
import time

logger = logging.getLogger("example")

if os.getenv("REDIS") == "1":
    from dramatiq.brokers.redis import RedisBroker
    broker = RedisBroker()
    dramatiq.set_broker(broker)


@dramatiq.actor(time_limit=5000, max_retries=3)
def long_running():
    while True:
        logger.info("Sleeping...")
        time.sleep(1)


def main(args):
    long_running.send()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
