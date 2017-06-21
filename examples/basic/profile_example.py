import dramatiq
import logging
import random
import sys
import time
import yappi

logger = logging.getLogger("example")
logformat = "[%(asctime)s] [PID %(process)d] [%(threadName)s] [%(name)s] [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=logformat)
logging.getLogger("pika").setLevel(logging.ERROR)


@dramatiq.actor
def add(x, y):
    if random.randint(1, 100) == 1:
        raise RuntimeError("an exception")


def prof(fn):
    def wrapper(*args, **kwargs):
        yappi.start()
        res = fn(*args, **kwargs)
        func_cols = {0: ("name", 160), 1: ("ncall", 5), 2: ("tsub", 8), 3: ("ttot", 8), 4: ("tavg", 8)}
        thread_cols = {0: ("name", 152), 1: ("id", 5), 2: ("tid", 16), 3: ("ttot", 8), 4: ("scnt", 8)}
        yappi.get_func_stats().sort("ttot").strip_dirs().print_all(columns=func_cols)
        yappi.get_thread_stats().print_all(columns=thread_cols)
        return res
    return wrapper


@prof
def main(args):
    broker = dramatiq.get_broker()
    broker.emit_after("process_boot")
    worker = dramatiq.Worker(broker, worker_threads=1)
    worker.start()

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    worker.stop()
    broker.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
