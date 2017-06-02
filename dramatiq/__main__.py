import argparse
import importlib
import logging
import multiprocessing
import os
import selectors
import signal
import sys
import time

from dramatiq import __version__, Broker, ConnectionError, Worker, get_broker
from threading import Thread

#: The number of available cpus.
cpus = multiprocessing.cpu_count()

#: The logging format.
logformat = "[%(asctime)s] [PID %(process)d] [%(threadName)s] [%(name)s] [%(levelname)s] %(message)s"

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
            raise ImportError(f"{value!r} is not a Broker")
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


def setup_parent_logging(args):
    level = verbosity.get(args.verbose, logging.DEBUG)
    logging.basicConfig(level=level, format=logformat, stream=sys.stderr)
    return logging.getLogger("MainProcess")


def setup_worker_logging(args, worker_id, logging_pipe):
    level = verbosity.get(args.verbose, logging.DEBUG)
    logging.basicConfig(level=level, format=logformat, stream=logging_pipe)
    return logging.getLogger(f"WorkerProcess({worker_id})")


def worker_process(args, worker_id, logging_fd):
    try:
        logging_pipe = os.fdopen(logging_fd, "w")
        logger = setup_worker_logging(args, worker_id, logging_pipe)
        broker = import_broker(args.broker)
        for module in args.modules:
            importlib.import_module(module)

        worker = Worker(broker, worker_threads=args.threads)
        worker.start()
    except ConnectionError as e:
        logger.critical("Broker connection failed. %s", e)
        return os._exit(1)

    def sighandler(signum, frame):
        nonlocal running
        if running:
            logger.info("Stopping worker process...")
            running = False
        else:
            logger.warn("Killing worker process...")
            return os._exit(1)

    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, sighandler)

    running = True
    while running:
        time.sleep(1)

    worker.stop()
    broker.close()
    logging_pipe.close()


def main():
    args = parse_arguments()
    worker_pipes = {}
    worker_processes = []
    for worker_id in range(args.processes):
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid != 0:
            os.close(write_fd)
            worker_pipes[worker_id] = os.fdopen(read_fd)
            worker_processes.append(pid)
            continue

        os.close(read_fd)
        return worker_process(args, worker_id, write_fd)

    logger = setup_parent_logging(args)
    running = True

    def watch(worker_pipes):
        nonlocal running
        selector = selectors.DefaultSelector()
        for pipe in worker_pipes.values():
            selector.register(pipe, selectors.EVENT_READ)

        while running:
            events = selector.select()
            for key, mask in events:
                sys.stderr.write(key.fileobj.readline())

    watcher = Thread(target=watch, args=(worker_pipes,), daemon=True)
    watcher.start()

    def sighandler(signum, frame):
        nonlocal worker_processes
        logger.info("Stopping worker processes...")
        for pid in worker_processes:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                logger.warning("Failed to terminate child process.", exc_info=True)

    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    for pid in worker_processes:
        os.waitpid(pid, 0)

    running = False
    watcher.join()
    return 0


if __name__ == "__main__":
    sys.exit(main())
