# This file is a part of Dramatiq.
#
# Copyright (C) 2017,2018,2019 CLEARTYPE SRL <bogdan@cleartype.io>
#
# Dramatiq is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# Dramatiq is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import annotations

# Don't depend on *anything* in this module.  The contents of this
# module can and *will* change without notice.
import argparse
import atexit
import functools
import importlib
import logging
import multiprocessing
import os
import random
import signal
import sys
import time
import types
from itertools import chain
from threading import Event, Thread
from typing import Optional, Set

from dramatiq import (
    Broker,
    ConnectionError,
    Worker,
    __version__,
    get_broker,
    get_logger,
)
from dramatiq.canteen import Canteen, canteen_add, canteen_get, canteen_try_init
from dramatiq.compat import StreamablePipe, file_or_stderr

try:
    from .watcher import setup_file_watcher

    HAS_WATCHDOG = True
except ImportError:  # pragma: no cover
    HAS_WATCHDOG = False

#: The exit codes that the master process returns.
RET_OK = 0  # The process terminated successfully.
RET_KILLED = 1  # The process was killed.
RET_IMPORT = 2  # Module import(s) failed or invalid command line argument.
RET_CONNECT = 3  # Broker connection failed during worker startup.
RET_PIDFILE = 4  # PID file points to an existing process or cannot be written to.

#: The size of the logging buffer.
BUFSIZE = 65536

#: The number of available cpus.
CPUS = multiprocessing.cpu_count()

#: The logging format.
LOGFORMAT = "[%(asctime)s] [PID %(process)d] [%(threadName)s] [%(name)s] [%(levelname)s] %(message)s"

#: The logging verbosity levels.
VERBOSITY = {
    0: logging.INFO,
    1: logging.DEBUG,
}

#: Message printed after the help text.
HELP_EPILOG = """\
examples:
  # Run dramatiq workers with actors defined in `./some_module.py`.
  $ dramatiq some_module

  # Run with a broker named "redis_broker" defined in "some_module".
  $ dramatiq some_module:redis_broker

  # Run with a broker named "broker" defined as attribute of "app" in "some_module".
  $ dramatiq some_module:app.broker

  # Run with a callable that sets up a broker.
  $ dramatiq some_module:setup_broker

  # Auto-reload dramatiq when files in the current directory change.
  $ dramatiq --watch . some_module

  # Run dramatiq with 1 thread per process.
  $ dramatiq --threads 1 some_module

  # Run dramatiq with gevent.  Make sure you `pip install gevent` first.
  $ dramatiq-gevent --processes 1 --threads 1024 some_module

  # Import extra modules.  Useful when your main module doesn't import
  # all the modules you need.
  $ dramatiq some_module some_other_module

  # Listen only to the "foo" and "bar" queues.
  $ dramatiq some_module -Q foo bar

  # Write the main process pid to a file.
  $ dramatiq some_module --pid-file /tmp/dramatiq.pid

  # Write logs to a file.
  $ dramatiq some_module --log-file /tmp/dramatiq.log
"""


def import_object(value):
    modname, varname = value, None
    if ":" in value:
        modname, varname = value.split(":", 1)

    module = importlib.import_module(modname)
    if varname is not None:
        varnames = varname.split(".")
        try:
            return module, functools.reduce(getattr, varnames, module)
        except AttributeError:
            raise ImportError("Module %r does not define a %r variable." % (modname, varname)) from None
    return module, None


def import_broker(value):
    module, broker_or_callable = import_object(value)
    if broker_or_callable is None:
        return module, get_broker()

    if callable(broker_or_callable):
        broker_or_callable()
        return module, get_broker()

    if not isinstance(broker_or_callable, Broker):
        raise ImportError("%r is not a Broker." % value)
    return module, broker_or_callable


def folder_path(value):
    if not os.path.isdir(value):
        raise argparse.ArgumentError("%r is not a valid directory" % value)
    return os.path.abspath(value)


def worker_fork_timeout_type(value: str) -> float:
    try:
        ms = float(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError("worker-fork-timeout be a number.") from e

    if ms < 10:
        raise argparse.ArgumentTypeError("worker-fork-timeout too small (minimum recommended: 10ms).")

    if ms > 1_800_000:
        raise argparse.ArgumentTypeError("worker-fork-timeout too large (maximum: 30 minutes).")

    return ms


def make_argument_parser():
    parser = argparse.ArgumentParser(
        prog="dramatiq",
        description="Run dramatiq workers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=HELP_EPILOG,
    )
    parser.add_argument(
        "broker",
        help="the broker to use (eg: 'module' or 'module:a_broker')",
    )
    parser.add_argument(
        "modules",
        metavar="module",
        nargs="*",
        help="additional python modules to import",
    )
    parser.add_argument(
        "--processes",
        "-p",
        default=CPUS,
        type=int,
        help="the number of worker processes to run (default: %s)" % CPUS,
    )
    parser.add_argument(
        "--threads",
        "-t",
        default=8,
        type=int,
        help="the number of worker threads per process (default: 8)",
    )
    parser.add_argument(
        "--path",
        "-P",
        default=".",
        nargs="*",
        type=str,
        help="the module import path (default: .)",
    )
    parser.add_argument(
        "--queues",
        "-Q",
        nargs="*",
        type=str,
        help="listen to a subset of queues (default: all queues)",
    )
    parser.add_argument(
        "--pid-file",
        type=str,
        help="write the PID of the master process to a file (default: no pid file)",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        help="write all logs to a file (default: sys.stderr)",
    )
    parser.add_argument("--skip-logging", action="store_true", help="do not call logging.basicConfig()")
    _unix_default = "fork" if sys.version_info < (3, 14) else "forkserver"
    parser.add_argument(
        "--use-spawn",
        action="store_true",
        help=f"start processes by spawning (default: {_unix_default} on unix, spawn on Windows and macOS)",
    )
    parser.add_argument(
        "--fork-function",
        "-f",
        action="append",
        dest="forks",
        default=[],
        help="fork a subprocess to run the given function",
    )
    parser.add_argument(
        "--worker-fork-timeout",
        type=worker_fork_timeout_type,
        default=30_000,
        help=(
            "timeout for wait all worker processes to come online before starting the fork processes. "
            "In milliseconds (default: 30 seconds)"
        ),
    )
    parser.add_argument(
        "--worker-shutdown-timeout",
        type=int,
        default=600000,
        help="timeout for worker shutdown, in milliseconds (default: 10 minutes)",
    )

    if HAS_WATCHDOG:
        parser.add_argument(
            "--watch",
            type=folder_path,
            metavar="DIR",
            help=(
                "watch a directory and reload the workers when any source files "
                "change (this feature must only be used during development). "
                "This option is currently only supported on unix systems."
            ),
        )
        parser.add_argument(
            "--watch-use-polling",
            action="store_true",
            help="poll the filesystem for changes rather than using a system-dependent filesystem event emitter",
        )
        parser.add_argument(
            "-i",
            "--watch-include",
            action="append",
            dest="include_patterns",
            default=["**.py"],
            help="Patterns to include when watching for changes. Always includes all python files (*.py).",
        )
        parser.add_argument(
            "-x",
            "--watch-exclude",
            action="append",
            dest="exclude_patterns",
            help="Patterns to ignore when watching for changes",
        )

    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--verbose", "-v", action="count", default=0, help="turn on verbose log output")
    return parser


HANDLED_SIGNALS: Set[signal.Signals] = {signal.SIGINT, signal.SIGTERM}
if hasattr(signal, "SIGHUP"):
    HANDLED_SIGNALS.add(signal.SIGHUP)
if hasattr(signal, "SIGBREAK"):
    HANDLED_SIGNALS.add(signal.SIGBREAK)


def try_block_signals():
    """Blocks HANDLED_SIGNALS on platforms that support it."""
    if hasattr(signal, "pthread_sigmask"):
        signal.pthread_sigmask(signal.SIG_BLOCK, HANDLED_SIGNALS)


def try_unblock_signals():
    """Unblocks HANDLED_SIGNALS on platforms that support it."""
    if hasattr(signal, "pthread_sigmask"):
        signal.pthread_sigmask(signal.SIG_UNBLOCK, HANDLED_SIGNALS)


def setup_pidfile(filename):
    try:
        pid = os.getpid()
        with open(filename, "r") as pid_file:
            old_pid = int(pid_file.read().strip())
            # This can happen when reloading the process via SIGHUP.
            if old_pid == pid:
                return pid

        try:
            os.kill(old_pid, 0)
            raise RuntimeError("Dramatiq is already running with PID %d." % old_pid)
        except OSError:
            try:
                os.remove(filename)
            except FileNotFoundError:
                pass

    except FileNotFoundError:  # pragma: no cover
        pass

    except ValueError:
        # Abort here to avoid overwriting real files.  Eg. someone
        # accidentally specifies a config file as the pid file.
        raise RuntimeError("PID file contains garbage. Aborting.") from None

    try:
        with open(filename, "w") as pid_file:
            pid_file.write(str(pid))

        # Change permissions to -rw-r--r--.
        os.chmod(filename, 0o644)
        return pid
    except (FileNotFoundError, PermissionError) as e:
        raise RuntimeError("Failed to write PID file %r. %s." % (e.filename, e.strerror)) from None


def remove_pidfile(filename, logger):
    try:
        logger.debug("Removing PID file %r.", filename)
        os.remove(filename)
    except FileNotFoundError:  # pragma: no cover
        logger.debug("Failed to remove PID file. It's gone.")


def setup_parent_logging(args, *, stream=sys.stderr):
    level = VERBOSITY.get(args.verbose, logging.DEBUG)
    if not args.skip_logging:
        logging.basicConfig(level=level, format=LOGFORMAT, stream=stream)

    return get_logger("dramatiq", "MainProcess")


def make_logging_setup(prefix):
    def setup_logging(args, child_id, logging_pipe):
        # Redirect all output to the logging pipe so that all output goes
        # to stderr and output is serialized so there isn't any mangling.
        sys.stdout = logging_pipe
        sys.stderr = logging_pipe

        level = VERBOSITY.get(args.verbose, logging.DEBUG)
        if not args.skip_logging:
            logging.basicConfig(level=level, format=LOGFORMAT, stream=logging_pipe)

        logging.getLogger("pika").setLevel(logging.CRITICAL)
        return get_logger("dramatiq", "%s(%s)" % (prefix, child_id))

    return setup_logging


setup_worker_logging = make_logging_setup("WorkerProcess")
setup_fork_logging = make_logging_setup("ForkProcess")


def watch_logs(log_filename, pipes, stop):
    with file_or_stderr(log_filename, mode="a", encoding="utf-8") as log_file:
        while pipes and not stop.is_set():
            try:
                events = multiprocessing.connection.wait(pipes, timeout=1)
                for event in events:
                    try:
                        while event.poll():
                            try:
                                data = event.recv_bytes()
                            except EOFError:
                                event.close()
                                raise

                            data = data.decode("utf-8", errors="replace")
                            log_file.write(data)
                            log_file.flush()
                    except BrokenPipeError:
                        event.close()
                        raise
            # If one of the worker processes is killed, its handle will be
            # closed so waiting for it is going to fail with this OSError.
            # Additionally, event.recv() raises EOFError when its pipe
            # is closed, and event.poll() raises BrokenPipeError when
            # its pipe is closed.  When any of these events happen, we
            # just take the closed pipes out of the waitlist.
            except (EOFError, OSError):
                pipes = [p for p in pipes if not p.closed]


def worker_process(args, worker_id, logging_pipe, canteen, event):
    running = True

    def termhandler(signum, frame):
        nonlocal running
        if running:
            logger.info("Stopping worker process...")
            running = False
        else:
            logger.warning("Killing worker process...")
            return sys.exit(RET_KILLED)

    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, termhandler)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, termhandler)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, termhandler)

    # Unblock the blocked signals inherited from the parent process
    # before we start any worker threads and trigger middleware hooks.
    try_unblock_signals()
    try:
        # Re-seed the random number generator from urandom on
        # supported platforms.  This should make it so that worker
        # processes don't all follow the same sequence.
        random.seed()

        logger = setup_worker_logging(args, worker_id, logging_pipe)
        logger.debug("Loading broker...")
        module, broker = import_broker(args.broker)
        broker.emit_after("process_boot")

        logger.debug("Loading modules...")
        for module in args.modules:
            importlib.import_module(module)

        with canteen_try_init(canteen) as acquired:
            if acquired:
                logger.debug("Sending forks to main process...")
                for middleware in broker.middleware:
                    for fork in middleware.forks:
                        fork_path = "%s:%s" % (fork.__module__, fork.__name__)
                        canteen_add(canteen, fork_path)

        logger.debug("Starting worker threads...")
        worker = Worker(broker, queues=args.queues, worker_threads=args.threads)
        worker.start()
    except ImportError:
        logger.exception("Failed to import module.")
        return sys.exit(RET_IMPORT)
    except ConnectionError:
        logger.exception("Broker connection failed.")
        return sys.exit(RET_CONNECT)
    finally:
        # Signal to the master process that this process has booted,
        # regardless of whether it failed or not.  If it did fail, the
        # worker process will realize that soon enough.
        event.set()

    logger.info("Worker process is ready for action.")

    while running:
        time.sleep(1)

    worker.stop(timeout=args.worker_shutdown_timeout)
    broker.close()
    logging_pipe.close()


def fork_process(args, fork_id, fork_path, logging_pipe):
    try:
        # Re-seed the random number generator from urandom on
        # supported platforms.  This should make it so that worker
        # processes don't all follow the same sequence.
        random.seed()

        logger = setup_fork_logging(args, fork_id, logging_pipe)
        logger.debug("Loading fork function...")

        _, func = import_object(fork_path)
    except ImportError:
        logger.exception("Failed to import module.")
        return sys.exit(RET_IMPORT)

    stopped = False

    def termhandler(signum, frame):
        nonlocal stopped
        if stopped:
            logger.warning("Killing fork process...")
            return sys.exit(RET_KILLED)
        else:
            logger.info("Stopping fork process...")
            stopped = True
            return sys.exit(RET_OK)

    logger.info("Fork process %r is ready for action.", fork_path)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, termhandler)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, termhandler)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, termhandler)

    # Unblock the blocked signals inherited from the parent process.
    try_unblock_signals()

    return sys.exit(func())


def main(args=None):  # noqa: C901
    args = args or make_argument_parser().parse_args()
    for path in args.path:
        sys.path.insert(0, path)

    if args.use_spawn:
        multiprocessing.set_start_method("spawn")

    try:
        if args.pid_file:
            setup_pidfile(args.pid_file)
    except RuntimeError as e:
        with file_or_stderr(args.log_file) as stream:
            logger = setup_parent_logging(args, stream=stream)
            logger.critical(e)
            return RET_PIDFILE

    canteen = multiprocessing.Value(Canteen)

    # To prevent the main process from exiting due to signals after worker
    # processes and fork processes have been defined but before the signal
    # handling has been configured for those processes, block those signals
    # that the main process is expected to handle.
    try_block_signals()

    worker_pipes = []
    worker_processes = []
    worker_process_events = []
    for worker_id in range(args.processes):
        read_pipe, write_pipe = multiprocessing.Pipe(duplex=False)
        event = multiprocessing.Event()
        proc = multiprocessing.Process(
            target=worker_process,
            args=(args, worker_id, StreamablePipe(write_pipe), canteen, event),
            daemon=False,
        )
        proc.start()
        worker_pipes.append(read_pipe)
        worker_processes.append(proc)
        worker_process_events.append(event)
        write_pipe.close()

    # Wait for all worker processes to come online before starting the
    # fork processes.  This is required to avoid race conditions like
    # in #297, #701.
    for event in worker_process_events:
        if proc.is_alive():
            if not event.wait(timeout=args.worker_fork_timeout / 1000):
                break

    fork_pipes = []
    fork_processes = []
    for fork_id, fork_path in enumerate(chain(args.forks, canteen_get(canteen))):
        read_pipe, write_pipe = multiprocessing.Pipe(duplex=False)
        proc = multiprocessing.Process(
            target=fork_process,
            args=(args, fork_id, fork_path, StreamablePipe(write_pipe)),
            daemon=True,
        )
        proc.start()
        fork_pipes.append(read_pipe)
        fork_processes.append(proc)
        write_pipe.close()

    parent_read_pipe, parent_write_pipe = multiprocessing.Pipe(duplex=False)
    logger = setup_parent_logging(args, stream=StreamablePipe(parent_write_pipe))
    logger.info("Dramatiq %r is booting up." % __version__)
    if args.pid_file:
        atexit.register(remove_pidfile, args.pid_file, logger)

    running, reload_process = True, False

    # The file watcher and log watcher threads should inherit the
    # signal blocking behaviour, so do not unblock the signals when
    # starting those threads.
    if HAS_WATCHDOG and args.watch:
        if not hasattr(signal, "SIGHUP"):
            raise RuntimeError("Watching for source changes is not supported on %s." % sys.platform)
        file_watcher = setup_file_watcher(
            args.watch,
            args.watch_use_polling,
            args.include_patterns,
            args.exclude_patterns,
        )

    log_watcher_stop_event = Event()
    log_watcher = Thread(
        target=watch_logs,
        args=(
            args.log_file,
            [parent_read_pipe, *worker_pipes, *fork_pipes],
            log_watcher_stop_event,
        ),
        daemon=False,
    )
    log_watcher.start()

    def stop_subprocesses(signum: signal.Signals):
        nonlocal running
        running = False

        for proc in chain(worker_processes, fork_processes):
            try:
                os.kill(proc.pid, signum.value)
            except OSError:  # pragma: no cover
                if proc.exitcode is None:
                    logger.warning("Failed to send %r to PID %d.", signum.name, proc.pid)

    def sighandler(signum: int, frame: Optional[types.FrameType]):
        nonlocal reload_process
        signum = signal.Signals(signum)

        reload_process = signum == getattr(signal, "SIGHUP", None)
        if signum == signal.SIGINT:
            signum = signal.SIGTERM

        logger.info("Sending signal %r to subprocesses...", signum.name)
        stop_subprocesses(signum)

    retcode = RET_OK
    for sig in HANDLED_SIGNALS:
        signal.signal(sig, sighandler)

    # Now that the watcher threads have been started and the
    # sighandler for the main process has been defined, it should be
    # safe to unblock the signals that were previously blocked.
    try_unblock_signals()

    # Wait for all workers to terminate.  If any of the processes
    # terminates unexpectedly, then shut down the rest as well.  The
    # use of `waited' here avoids a race condition where the processes
    # could potentially exit before we even get a chance to wait on
    # them.
    waited = False
    while not waited or any(p.exitcode is None for p in worker_processes):
        waited = True
        for proc in worker_processes:
            proc.join(timeout=1)
            if proc.exitcode is None:
                continue

            if running:  # pragma: no cover
                logger.critical(
                    "Worker with PID %r exited unexpectedly (code %r). Shutting down...",
                    proc.pid,
                    proc.exitcode,
                )
                stop_subprocesses(signal.SIGTERM)
                retcode = proc.exitcode
                break

            else:
                retcode = retcode or proc.exitcode

    # The log watcher can't be a daemon in case we log to a file so we
    # have to wait for it to complete on exit.
    log_watcher_stop_event.set()
    log_watcher.join()

    if HAS_WATCHDOG and args.watch:
        file_watcher.stop()
        file_watcher.join()

    if reload_process:
        if sys.argv[0].endswith("/dramatiq/__main__.py"):
            return os.execvp(sys.executable, ["python", "-m", "dramatiq", *sys.argv[1:]])
        return os.execvp(sys.argv[0], sys.argv)

    return RET_KILLED if retcode < 0 else retcode
