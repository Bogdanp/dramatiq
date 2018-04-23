import argparse
import json
import os
import sys
import time

import dramatiq
from dramatiq.middleware import Shutdown

if os.getenv("REDIS") == "1":
    from dramatiq.brokers.redis import RedisBroker
    broker = RedisBroker()
    dramatiq.set_broker(broker)


def path_to(*xs):
    return os.path.abspath(os.path.join(os.path.dirname(__file__), *(str(x) for x in xs)))


def load_state(n):
    try:
        with open(path_to("states", n), "r") as f:
            data = json.load(f)
    except Exception:
        fib.logger.info("Could not read state file, using defaults.")
        return 1, 1, 0

    i, x2, x1 = data["i"], data["x2"], data["x1"]
    fib.logger.info("Resuming fib(%d) from iteration %d.", n, i)
    return i, x2, x1


def dump_state(n, state):
    os.makedirs("states", exist_ok=True)
    with open(path_to("states", n), "w") as f:
        json.dump(state, f)

    fib.logger.info("Dumped fib(%d) state for iteration %d.", n, state["i"])


def remove_state(n):
    try:
        os.remove(path_to("states", n))
    except OSError:
        pass

    fib.logger.info("Deleted state for fib(%d).", n)


@dramatiq.actor(time_limit=float("inf"), notify_shutdown=True, max_retries=0)
def fib(n):
    i, x2, x1 = load_state(n)

    try:
        for i in range(i, n + 1):
            state = {
                "i": i,
                "x2": x2,
                "x1": x1,
            }

            x2, x1 = x1, x2 + x1
            fib.logger.info("fib(%d): %d", i, x1)
            time.sleep(.1)

        remove_state(n)
        fib.logger.info("Done!")
    except Shutdown:
        dump_state(n, state)


def main(args):
    parser = argparse.ArgumentParser(description="Calculates fib(n)")
    parser.add_argument("n", type=int, help="must be a positive number")
    args = parser.parse_args()
    fib.send(args.n)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
