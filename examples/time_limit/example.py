import dramatiq
import logging
import os
import sys
import time

if os.getenv("REDIS") == "1":
    from dramatiq.brokers.redis import RedisBroker
    broker = RedisBroker()
    dramatiq.set_broker(broker)


@dramatiq.actor(time_limit=5000, max_retries=3)
def long_running():
    logger = logging.getLogger("long_running")

    while True:
        logger.info("Sleeping...")
        time.sleep(1)


@dramatiq.actor(time_limit=5000, max_retries=0)
def long_running_with_catch():
    logger = logging.getLogger("long_running_with_catch")

    try:
        while True:
            logger.info("Sleeping...")
            time.sleep(1)
    except dramatiq.middleware.time_limit.TimeLimitExceeded:
        logger.warning("Time limit exceeded. Aborting...")


def main(args):
    long_running.send()
    long_running_with_catch.send()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
