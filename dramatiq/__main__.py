import argparse
import importlib
import logging
import multiprocessing
import multiprocessing.managers
import multiprocessing.pool
import sys
import time

from dramatiq import __version__, Broker, Worker, get_broker

#: The number of available cpus.
cpus = multiprocessing.cpu_count()

#: The logging format.
logformat = "[%(asctime)s] [%(processName)s] [%(threadName)s] [%(name)s] [%(levelname)s] %(message)s"

#: The logging verbosity levels.
verbosity = {
    0: logging.INFO,
    1: logging.DEBUG,
}


def import_broker(value):
    module, name = value, None
    if ":" in value:
        module, name = value.split(":", 1)

    module = importlib.import_module(module)
    if name is not None:
        broker = getattr(module, name, None)
        if not isinstance(broker, Broker):
            raise TypeError(f"{value!r} is not a broker instance")
        return broker
    return get_broker()


def parse_arguments():
    parser = argparse.ArgumentParser(prog="dramatiq", description="Run dramatiq workers.")
    parser.add_argument("broker", help="the broker to use (eg: foo_module or foo_module:some_broker)")
    parser.add_argument("modules", metavar="module", nargs="*", help="additional python modules to import")
    parser.add_argument("--processes", "-p", default=cpus, type=int, help="the number of worker processes to run")
    parser.add_argument("--threads", "-t", default=8, type=int, help="the number of worker threads per process")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--verbose", "-v", action="count", default=0, help="control logging verbosity")
    return parser.parse_args()


def worker_process(broker, modules, worker_threads):
    broker = import_broker(broker)
    for module in modules:
        importlib.import_module(module)

    worker = Worker(broker, worker_threads=worker_threads)
    worker.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        worker.stop()


def main():
    args = parse_arguments()
    level = verbosity.get(args.verbose, logging.DEBUG)
    logging.basicConfig(level=level, format=logformat)

    with multiprocessing.pool.Pool(processes=args.processes) as pool:
        futures = []
        for _ in range(args.processes):
            future = pool.apply_async(worker_process, args=(args.broker, args.modules, args.threads))
            futures.append(future)

        for future in futures:
            try:
                future.get()

            except KeyboardInterrupt:
                pass

            except BaseException as e:
                logging.critical(e)
                return 1

    pool.join()
    return 0


if __name__ == "__main__":
    sys.exit(main())
