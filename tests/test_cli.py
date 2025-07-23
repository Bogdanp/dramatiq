from __future__ import annotations

import os
import signal
import time
from subprocess import PIPE, STDOUT

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.common import current_millis
from dramatiq.middleware import Middleware

from .common import skip_on_windows

fakebroker = object()


class BrokerHolder:
    fakebroker = object()


broker = RedisBroker()
loaded_at = current_millis()
fork_function_signal_mask_write_path = "/tmp/dramatiq-cli-fork-function-blocked-signals"
middleware_fork_signal_mask_write_path = "/tmp/dramatiq-cli-middleware-fork-blocked-signals"
consumer_signal_mask_write_path = "/tmp/dramatiq-cli-consumer-blocked-signals"
after_process_boot_signal_mask_write_path = "/tmp/dramatiq-cli-boot-blocked-signals"


@dramatiq.actor(broker=broker)
def write_loaded_at(filename):
    with open(filename, "w") as f:
        f.write(str(loaded_at))


@dramatiq.actor(broker=broker)
def write_masked_signals(filename):
    current_sigmask = sorted(signal.pthread_sigmask(signal.SIG_BLOCK, []))
    with open(filename, "w") as f:
        f.write(f"current_sigmask={current_sigmask}")


def fork_function_write_masked_signals():
    current_sigmask = sorted(signal.pthread_sigmask(signal.SIG_BLOCK, []))
    print("Writing to fork function path")
    with open(fork_function_signal_mask_write_path, "w") as f:
        f.write(f"current_sigmask={current_sigmask}")


class ConsumerThreadMaskWritingMiddleware(Middleware):
    def before_ack(self, _broker, _message):
        current_sigmask = sorted(signal.pthread_sigmask(signal.SIG_BLOCK, []))
        with open(consumer_signal_mask_write_path, "w") as f:
            f.write(f"current_sigmask={current_sigmask}")


consumer_mask_writing_broker = RedisBroker(middleware=[ConsumerThreadMaskWritingMiddleware()])


@dramatiq.actor(broker=consumer_mask_writing_broker)
def consumer_write_masked_signals():
    return None


def fork_middleware_write_masked_signals():
    current_sigmask = sorted(signal.pthread_sigmask(signal.SIG_BLOCK, []))
    with open(middleware_fork_signal_mask_write_path, "w") as f:
        f.write(f"current_sigmask={current_sigmask}")


class ForkMaskWritingMiddleware(Middleware):
    @property
    def forks(self):
        return [fork_middleware_write_masked_signals]


middleware_fork_mask_writing_broker = RedisBroker(middleware=[ForkMaskWritingMiddleware()])


@dramatiq.actor(broker=middleware_fork_mask_writing_broker)
def middleware_fork_actor():
    return None


class AfterProcessBootMaskWritingMiddleware(Middleware):
    def after_process_boot(self, broker):
        current_sigmask = sorted(signal.pthread_sigmask(signal.SIG_BLOCK, []))
        with open(after_process_boot_signal_mask_write_path, "w") as f:
            f.write(f"current_sigmask={current_sigmask}")


after_process_boot_mask_writing_broker = RedisBroker(middleware=[AfterProcessBootMaskWritingMiddleware()])


@dramatiq.actor(broker=after_process_boot_mask_writing_broker)
def after_process_boot_actor():
    return None


@skip_on_windows
def test_cli_fails_to_start_given_an_invalid_broker_name(start_cli):
    # Given that this module doesn't define a broker called "idontexist"
    # When I start the cli and point it at that broker
    proc = start_cli("tests.test_cli:idontexist", stdout=PIPE, stderr=STDOUT)
    proc.wait(60)

    # Then the process return code should be 2
    assert proc.returncode == 2

    # And the output should contain an error
    assert b"Module 'tests.test_cli' does not define a 'idontexist' variable." in proc.stdout.read()


@skip_on_windows
def test_cli_fails_to_start_given_an_invalid_broker_instance(start_cli):
    # Given that this module defines a "fakebroker" variable that's not a Broker
    # When I start the cli and point it at that broker
    proc = start_cli("tests.test_cli:fakebroker", stdout=PIPE, stderr=STDOUT)
    proc.wait(60)

    # Then the process return code should be 2
    assert proc.returncode == 2

    # And the output should contain an error
    assert b"'tests.test_cli:fakebroker' is not a Broker." in proc.stdout.read()


@skip_on_windows
def test_cli_fails_to_start_given_an_invalid_nested_broker_instance(start_cli):
    # Given that this module defines a "BrokerHolder.fakebroker" variable that's not a Broker
    # When I start the cli and point it at that broker
    proc = start_cli("tests.test_cli:BrokerHolder.fakebroker", stdout=PIPE, stderr=STDOUT)
    proc.wait(60)

    # Then the process return code should be 2
    assert proc.returncode == 2

    # And the output should contain an error
    assert b"'tests.test_cli:BrokerHolder.fakebroker' is not a Broker." in proc.stdout.read()


@skip_on_windows
def test_cli_can_be_reloaded_on_sighup(start_cli):
    # Given that I have a shared file the processes can use to communicate with
    filename = "/tmp/dramatiq-cli-loaded-at"

    # When I start my workers
    proc = start_cli(
        "tests.test_cli:broker",
        extra_args=[
            "--processes",
            "1",
            "--threads",
            "1",
        ],
    )

    # And enqueue a task to write the loaded timestamp
    write_loaded_at.send(filename)
    broker.join(write_loaded_at.queue_name)

    # Then I expect a timestamp to have been written to the file
    with open(filename, "r") as f:
        timestamp_1 = int(f.read())

    # When I send a SIGHUP signal
    os.kill(proc.pid, signal.SIGHUP)

    # And wait for the workers to reload
    time.sleep(5)

    # And write another timestamp
    write_loaded_at.send(filename)
    broker.join(write_loaded_at.queue_name)

    # Then I expect another timestamp to have been written to the file
    with open(filename, "r") as f:
        timestamp_2 = int(f.read())

    # And the second time to be at least a second apart from the first
    assert timestamp_2 - timestamp_1 >= 1000


@skip_on_windows
def test_worker_threads_have_no_blocked_signals(start_cli):
    # Given that I have a shared file the processes can use to communicate with
    filename = "/tmp/dramatiq-cli-worker-blocked-signals"

    # When I start my workers
    start_cli(
        "tests.test_cli:broker",
        extra_args=[
            "--processes",
            "1",
            "--threads",
            "1",
        ],
    )

    # And enqueue a task to write the blocked signals
    write_masked_signals.send(filename)
    broker.join(write_masked_signals.queue_name)

    # And then read the blocked signals to written to the file by the worker
    with open(filename, "r") as f:
        blocked_signals = f.read()

    # Then I expect that no signals are blocked
    assert blocked_signals == "current_sigmask=[]"


@skip_on_windows
def test_consumer_threads_have_no_blocked_signals(start_cli):
    # Given that I have a shared file the consumer threads can use to communicate
    filename = consumer_signal_mask_write_path

    # When I start workers on a custom broker with middleware to cause consumer threads to write masked signals
    start_cli(
        "tests.test_cli:consumer_mask_writing_broker",
        extra_args=[
            "--processes",
            "1",
            "--threads",
            "1",
        ],
    )

    # And enqueue a task for a worker
    consumer_write_masked_signals.send()
    consumer_mask_writing_broker.join(consumer_write_masked_signals.queue_name)

    # And then read the blocked signals written to the file by the consumer thread
    with open(filename, "r") as f:
        blocked_signals = f.read()

    # Then I expect that no signals are blocked
    assert blocked_signals == "current_sigmask=[]"


@skip_on_windows
def test_middleware_fork_functions_have_no_blocked_signals(start_cli):
    # Given that I have a shared file that the fork process can use to communicate
    filename = middleware_fork_signal_mask_write_path

    # When I start workers on a custom broker with middleware with a fork function that writes masked signals
    start_cli(
        "tests.test_cli:middleware_fork_mask_writing_broker",
        extra_args=[
            "--processes",
            "1",
            "--threads",
            "1",
        ],
    )

    # And enqueue a task for a worker, to wait for worker processes to finish setting up
    middleware_fork_actor.send()
    middleware_fork_mask_writing_broker.join(middleware_fork_actor.queue_name)

    # And wait long enough for the fork function to execute
    time.sleep(2)

    # And then read the blocked signals written to the file by the fork process
    with open(filename, "r") as f:
        blocked_signals = f.read()

    # Then I expect that no signals are blocked
    assert blocked_signals == "current_sigmask=[]"


@skip_on_windows
def test_cli_fork_functions_have_no_blocked_signals(start_cli):
    # Given that I have a shared file that the fork process can use to communicate
    filename = fork_function_signal_mask_write_path

    # When I start workers and a fork function
    start_cli(
        "tests.test_cli:broker",
        extra_args=[
            "--processes",
            "1",
            "--threads",
            "1",
            "--fork",
            "tests.test_cli:fork_function_write_masked_signals",
        ],
    )

    # And enqueue a task for a worker, to wait for worker processes to finish setting up
    write_masked_signals.send("/tmp/dramatiq-dummy-not-used")
    broker.join(write_masked_signals.queue_name)

    # And wait long enough for the fork function to execute
    time.sleep(2)

    # And then read the blocked signals written to the file by the fork process
    with open(filename, "r") as f:
        blocked_signals = f.read()

    # Then I expect that no signals are blocked
    assert blocked_signals == "current_sigmask=[]"


@skip_on_windows
def test_after_process_boot_call_has_no_blocked_signals(start_cli):
    # Given that I have a shared file that the fork process can use to communicate
    filename = after_process_boot_signal_mask_write_path

    # When I start workers on a custom broker with middleware with an after_process_boot
    # method that writes masked signals
    start_cli(
        "tests.test_cli:after_process_boot_mask_writing_broker",
        extra_args=[
            "--processes",
            "1",
            "--threads",
            "1",
        ],
    )

    # And enqueue a task for a worker
    after_process_boot_actor.send()
    after_process_boot_mask_writing_broker.join(after_process_boot_actor.queue_name)

    # And then read the blocked signals written to the file in the after_process_boot call
    with open(filename, "r") as f:
        blocked_signals = f.read()

    # Then I expect that no signals are blocked
    assert blocked_signals == "current_sigmask=[]"


@skip_on_windows
def test_cli_worker_fork_timeout_invalid_string(start_cli):
    proc = start_cli(
        "tests.test_cli:broker",
        extra_args=[
            "--processes",
            "1",
            "--threads",
            "1",
            "--worker-fork-timeout",
            "tests",
        ],
        stdout=PIPE,
        stderr=STDOUT,
    )
    proc.wait(60)

    # The process return code should be 2
    assert proc.returncode == 2

    # And the output should contain an error
    assert b"worker-fork-timeout be a number." in proc.stdout.read()


@skip_on_windows
def test_cli_worker_fork_timeout_invalid_str(start_cli):
    proc = start_cli(
        "tests.test_cli:broker",
        extra_args=[
            "--processes",
            "1",
            "--threads",
            "1",
            "--worker-fork-timeout",
            "tests",
        ],
        stdout=PIPE,
        stderr=STDOUT,
    )
    proc.wait(60)

    # The process return code should be 2
    assert proc.returncode == 2

    # And the output should contain an error
    assert b"worker-fork-timeout be a number." in proc.stdout.read()


@skip_on_windows
def test_cli_worker_fork_timeout_invalid_negative(start_cli):
    proc = start_cli(
        "tests.test_cli:broker",
        extra_args=[
            "--processes",
            "1",
            "--threads",
            "1",
            "--worker-fork-timeout",
            "-5",
        ],
        stdout=PIPE,
        stderr=STDOUT,
    )
    proc.wait(60)

    # The process return code should be 2
    assert proc.returncode == 2

    # And the output should contain an error
    assert b"worker-fork-timeout too small (minimum recommended: 10ms)." in proc.stdout.read()


@skip_on_windows
def test_cli_worker_fork_timeout_invalid_below_10(start_cli):
    proc = start_cli(
        "tests.test_cli:broker",
        extra_args=[
            "--processes",
            "1",
            "--threads",
            "1",
            "--worker-fork-timeout",
            "9",
        ],
        stdout=PIPE,
        stderr=STDOUT,
    )
    proc.wait(60)

    # The process return code should be 2
    assert proc.returncode == 2

    # And the output should contain an error
    assert b"worker-fork-timeout too small (minimum recommended: 10ms)." in proc.stdout.read()


@skip_on_windows
def test_cli_worker_fork_timeout_invalid_above_1_800_000(start_cli):
    proc = start_cli(
        "tests.test_cli:broker",
        extra_args=[
            "--processes",
            "1",
            "--threads",
            "1",
            "--worker-fork-timeout",
            "3_600_000",
        ],
        stdout=PIPE,
        stderr=STDOUT,
    )
    proc.wait(60)

    # The process return code should be 2
    assert proc.returncode == 2

    # And the output should contain an error
    assert b"worker-fork-timeout too large (maximum: 30 minutes)." in proc.stdout.read()
