import time
from pathlib import Path

import pytest

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.common import current_millis

from .common import skip_in_ci, skip_on_pypy, skip_on_windows

broker = RedisBroker()
loaded_at = current_millis()


@dramatiq.actor(broker=broker)
def write_loaded_at(filename):
    with open(filename, "w") as f:
        f.write(str(loaded_at))


@skip_in_ci
@skip_on_windows
@skip_on_pypy
@pytest.mark.parametrize("extra_args", [
    (),
    ("--watch-use-polling",),
])
def test_cli_can_watch_for_source_code_changes(start_cli, extra_args):
    # Given that I have a shared file the processes can use to communicate with
    filename = "/tmp/dramatiq-loaded-at"

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
    time.sleep(5)

    # And write another timestamp
    write_loaded_at.send(filename)
    broker.join(write_loaded_at.queue_name)

    # Then I expect another timestamp to have been written to the file
    with open(filename, "r") as f:
        timestamp_2 = int(f.read())

    # And the second time to be at least a second apart from the first
    assert timestamp_2 - timestamp_1 >= 1000

    # When I open a watched file, this should not trigger a reload
    last_loaded_at = timestamp_2
    with (Path("tests") / "test_watch.py").open("r"):
        time.sleep(5)
        write_loaded_at.send(filename)
        broker.join(write_loaded_at.queue_name)

    # Then I expect another timestamp to have been written to the file
    with open(filename, "r") as f:
        timestamp_3 = int(f.read())

    assert last_loaded_at == timestamp_3
