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


def get_state(n):
    try:
        with open(os.path.join('states', str(n)), 'r') as state:
            data = json.load(state)
            i, x2, x1 = data['i'], data['x2'], data['x1']
            fib.logger.debug('Resuming fib(%d) from iteration %d ...', n, i)
            return i, x2, x1
    except Exception:
        fib.logger.debug('Could not read state file, using defaults ...')
        return 1, 1, 0


def save_state(n, i, x2, x1):
    if not os.path.exists('states'):
        os.mkdir('states')
    with open(os.path.join('states', str(n)), 'w') as state:
        json.dump({'i': i, 'x2': x2, 'x1': x1}, state)
        fib.logger.debug('Saved fib(%d) state for iteration %d ...', n, i)


def del_state(n):
    file = os.path.join('states', str(n))
    if os.path.exists(file):
        os.remove(file)
        fib.logger.debug('Deleted state for fib(%d) ...', n)


@dramatiq.actor(time_limit=float('inf'), notify_shutdown=True, max_retries=0)
def fib(n):
    i, x2, x1 = get_state(n)

    try:
        for i in range(i, n + 1):
            state = {'i': i, 'x2': x2, 'x1': x1}

            x2, x1 = x1, (x2 + x1)
            fib.logger.info('fib(%d): %d', i, x1)
            time.sleep(.1)

        del_state(n)
        fib.logger.info('Done!')
    except Shutdown:
        save_state(n, **state)


def main(args):
    parser = argparse.ArgumentParser(description="Calculates fib(n)")
    parser.add_argument("n", type=int, help="must be a positive number")
    args = parser.parse_args()
    fib.send(args.n)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
