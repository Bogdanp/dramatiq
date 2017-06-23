import dramatiq
import sys
import time

from pympler import tracker

from .example import crawl  # noqa


def memprof(fn):
    def wrapper(*args, **kwargs):
        tr = tracker.SummaryTracker()
        res = fn(*args, **kwargs)
        tr.print_diff()
        return res
    return wrapper


@memprof
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
