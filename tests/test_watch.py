import os
import platform
import time
from pathlib import Path

import pytest

import remoulade
from remoulade.brokers.rabbitmq import RabbitmqBroker
from remoulade.common import current_millis

broker = RabbitmqBroker()
loaded_at = current_millis()

CURRENT_PLATFORM = platform.python_implementation()
CURRENT_OS = platform.system()


@remoulade.actor(broker=broker)
def write_loaded_at(filename):
    with open(filename, "w") as f:
        f.write(str(loaded_at))


@pytest.mark.skipif(os.getenv("TRAVIS") == "1", reason="test skipped on Travis")
@pytest.mark.skipif(CURRENT_PLATFORM == "PyPy", reason="Code reloading is not supported on PyPy.")
@pytest.mark.skipif(CURRENT_OS == "Windows", reason="Code reloading is not supported on Windows.")
@pytest.mark.parametrize("extra_args", [
    (),
    ("--watch-use-polling",),
])
def test_cli_can_watch_for_source_code_changes(start_cli, extra_args):
    # Given that I have a shared file the processes can use to communicate with
    filename = "/tmp/remoulade-loaded-at"

    # When I start my workers
    start_cli("tests.test_watch:broker", extra_args=[
        "--processes", "1",
        "--threads", "1",
        "--watch", "tests",
        *extra_args,
    ])

    # And enqueue a task to write the loaded timestamp
    write_loaded_at.send(filename)
    broker.join(write_loaded_at.queue_name)

    # Then I expect a timestamp to have been written to the file
    with open(filename, "r") as f:
        timestamp_1 = int(f.read())

    # When I then update a watched file's mtime
    (Path("tests") / "test_watch.py").touch()

    # And wait for the workers to reload
    time.sleep(1)

    # And write another timestamp
    write_loaded_at.send(filename)
    broker.join(write_loaded_at.queue_name)

    # Then I expect another timestamp to have been written to the file
    with open(filename, "r") as f:
        timestamp_2 = int(f.read())

    # And the second time to be at least a second apart from the first
    assert timestamp_2 - timestamp_1 >= 1000
