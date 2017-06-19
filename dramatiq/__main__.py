import argparse
import importlib
import logging
import multiprocessing
import os
import selectors
import signal
import sys
import time

from collections import defaultdict
from dramatiq import __version__, Broker, ConnectionError, Worker, get_broker, get_logger
from threading import Thread

try:
    import watchdog.events
    import watchdog.observers

    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

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
    modname, varname = value, None
    if ":" in value:
        modname, varname = value.split(":", 1)

    module = importlib.import_module(modname)
    if varname is not None:
        if not hasattr(module, varname):
            raise ImportError(f"Module {modname!r} does not define a {varname!r} variable.")

        broker = getattr(module, varname)
        if not isinstance(broker, Broker):
            raise ImportError(f"Variable {varname!r} from module {modname!r} is not a Broker.")
        return module, broker
    return module, get_broker()


def folder_path(value):
    if not os.path.isdir(value):
        raise argparse.ArgumentError(f"{value!r} is not a valid directory")
    return os.path.abspath(value)


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

    if HAS_WATCHDOG:
        parser.add_argument(
            "--watch", type=folder_path,
            help=(
                "watch a directory and reload the workers when any source files "
                "change (this feature must only be used during development)"
            )
        )

    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--verbose", "-v", action="count", default=0)
    return parser.parse_args()


def setup_parent_logging(args):
    level = verbosity.get(args.verbose, logging.DEBUG)
    logging.basicConfig(level=level, format=logformat, stream=sys.stderr)
    return get_logger("dramatiq", "MainProcess")


def setup_worker_logging(args, worker_id, logging_pipe):
    level = verbosity.get(args.verbose, logging.DEBUG)
    logging.basicConfig(level=level, format=logformat, stream=logging_pipe)
    logging.getLogger("pika").setLevel(logging.ERROR)
    return get_logger("dramatiq", f"WorkerProcess({worker_id})")


def worker_process(args, worker_id, logging_fd):
    try:
        logging_pipe = os.fdopen(logging_fd, "w")
        logger = setup_worker_logging(args, worker_id, logging_pipe)
        module, broker = import_broker(args.broker)
        broker.emit_after("process_boot")

        for module in args.modules:
            importlib.import_module(module)

        worker = Worker(broker, worker_threads=args.threads)
        worker.start()
    except ImportError as e:
        logger.critical(e)
        return os._exit(2)
    except ConnectionError as e:
        logger.critical("Broker connection failed. %s", e)
        return os._exit(3)

    def termhandler(signum, frame):
        nonlocal running
        if running:
            logger.info("Stopping worker process...")
            running = False
        else:
            logger.warning("Killing worker process...")
            return os._exit(1)

    logger.info("Worker process is ready for action.")
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, termhandler)
    signal.signal(signal.SIGHUP, termhandler)

    running = True
    while running:
        time.sleep(1)

    worker.stop()
    broker.close()
    logging_pipe.close()


def main_process(args):
    worker_pipes = []
    worker_processes = []
    for worker_id in range(args.processes):
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid != 0:
            os.close(write_fd)
            worker_pipes.append(os.fdopen(read_fd))
            worker_processes.append(pid)
            continue

        os.close(read_fd)
        return worker_process(args, worker_id, write_fd)

    logger = setup_parent_logging(args)
    logger.info(f"Dramatiq {__version__!r} is booting up.")
    running, reload_process = True, False

    if HAS_WATCHDOG and args.watch:
        file_event_handler = SourceChangesHandler(patterns=["*.py"])
        file_watcher = watchdog.observers.Observer()
        file_watcher.schedule(file_event_handler, args.watch, recursive=True)
        file_watcher.start()

    def watch_logs(worker_pipes):
        nonlocal running
        selector = selectors.DefaultSelector()
        for pipe in worker_pipes:
            selector.register(pipe, selectors.EVENT_READ)

        buffers = defaultdict(str)
        while running:
            events = selector.select(timeout=1)
            for key, mask in events:
                data = os.read(key.fd, 16384)
                if not data:
                    selector.unregister(key.fileobj)
                    sys.stderr.write(buffers[key.fd])
                    continue

                buffers[key.fd] += data.decode("utf-8")
                while buffers[key.fd]:
                    index = buffers[key.fd].find("\n")
                    if index == -1:
                        break

                    line = buffers[key.fd][:index + 1]
                    buffers[key.fd] = buffers[key.fd][index + 1:]

                    sys.stderr.write(line)
                    sys.stderr.flush()

        logger.debug("Closing selector...")
        selector.close()

    log_watcher = Thread(target=watch_logs, args=(worker_pipes,), daemon=True)
    log_watcher.start()

    def sighandler(signum, frame):
        nonlocal reload_process, worker_processes
        reload_process = signum == signal.SIGHUP
        signum = {
            signal.SIGINT: signal.SIGTERM,
            signal.SIGTERM: signal.SIGTERM,
            signal.SIGHUP: signal.SIGHUP,
        }[signum]

        logger.info("Sending %r to worker processes...", signum.name)
        for pid in worker_processes:
            try:
                os.kill(pid, signum)
            except OSError:
                logger.warning("Failed to send %r to child process.", signum.name, exc_info=True)

    retcode = 0
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    signal.signal(signal.SIGHUP, sighandler)
    for pid in worker_processes:
        pid, rc = os.waitpid(pid, 0)
        retcode = max(retcode, rc >> 8)

    running = False
    if HAS_WATCHDOG and args.watch:
        file_watcher.stop()
        file_watcher.join()

    log_watcher.join()
    for pipe in worker_pipes:
        pipe.close()

    if reload_process:
        return main_process(args)
    return retcode


def main():
    args = parse_arguments()
    return main_process(args)


if HAS_WATCHDOG:
    class SourceChangesHandler(watchdog.events.PatternMatchingEventHandler):
        def on_any_event(self, event):
            os.kill(os.getpid(), signal.SIGHUP)


if __name__ == "__main__":
    sys.exit(main())
