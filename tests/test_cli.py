import os
import signal
import time
from subprocess import PIPE, STDOUT

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.common import current_millis

from .common import skip_on_windows

fakebroker = object()


class BrokerHolder:
    fakebroker = object()


broker = RedisBroker()
loaded_at = current_millis()


@dramatiq.actor(broker=broker)
def write_loaded_at(filename):
    with open(filename, "w") as f:
        f.write(str(loaded_at))


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
    proc = start_cli("tests.test_cli:broker", extra_args=[
        "--processes", "1",
        "--threads", "1",
    ])

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
