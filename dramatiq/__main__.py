import argparse
import importlib
import logging
import multiprocessing
import os
import signal
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
    parser.add_argument(
        "broker",
        help="the broker to use (eg: 'some_module' or 'some_module:some_broker')",
    )
    parser.add_argument(
        "modules", metavar="module", nargs="*",
        help="additional python modules to import",
    )
    parser.add_argument(
        "--processes", "-p", default=cpus, type=int,
        help=f"the number of worker processes to run (default: {cpus})",
    )
    parser.add_argument(
        "--threads", "-t", default=8, type=int,
        help="the number of worker threads per process (default: 8)",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--verbose", "-v", action="count", default=0)
    return parser.parse_args()


def worker_process(broker, modules, worker_threads):
    broker = import_broker(broker)
    for module in modules:
        importlib.import_module(module)

    logger = logging.getLogger("WorkerProcess")
    worker = Worker(broker, worker_threads=worker_threads)
    worker.start()

    def sighandler(signum, frame):
        nonlocal running
        if not running:
            logger.warn("Murdering worker process...")
            sys.exit(1)

        logger.info("Shutting worker process down gracefully...")
        running = False

    os.setsid()
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, sighandler)

    running = True
    while running:
        time.sleep(1)

    worker.stop()
    broker.close()


def main():
    args = parse_arguments()
    level = verbosity.get(args.verbose, logging.DEBUG)
    logger = logging.getLogger("MainProcess")
    logging.basicConfig(level=level, format=logformat)

    worker_processes = []
    for _ in range(args.processes):
        pid = os.fork()
        if pid != 0:
            worker_processes.append(pid)
            continue

        return worker_process(args.broker, args.modules, args.threads)

    def sighandler(signum, frame):
        nonlocal worker_processes
        logger.info("Stopping worker processes...")
        for pid in worker_processes:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass

    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    for pid in worker_processes:
        os.waitpid(pid, 0)

    return 0


if __name__ == "__main__":
    sys.exit(main())
