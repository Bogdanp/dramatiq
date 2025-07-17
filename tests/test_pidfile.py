from __future__ import annotations

import os
import signal
import time

from dramatiq.brokers.stub import StubBroker

from .common import skip_on_windows

broker = StubBroker()


def remove(filename):
    try:
        os.remove(filename)
    except OSError:
        pass


@skip_on_windows
def test_cli_scrubs_stale_pid_files(start_cli):
    try:
        # Given that I have an existing file containing an old pid
        filename = "test_scrub.pid"
        with open(filename, "w") as f:
            f.write("999999")

        # When I try to start the cli and pass that file as a PID file
        proc = start_cli("tests.test_pidfile:broker", extra_args=["--pid-file", filename])

        # And I wait for it to write the pid file
        time.sleep(1)

        # Then the process should write its pid to the file
        with open(filename, "r") as f:
            pid = int(f.read())

        assert pid == proc.pid

        # When I stop the process
        proc.terminate()
        proc.wait()

        # Then the process should exit with return code 0
        assert proc.returncode == 0

        # And the file should be removed
        assert not os.path.exists(filename)
    finally:
        remove(filename)


def test_cli_aborts_when_pidfile_contains_garbage(start_cli):
    try:
        # Given that I have an existing file containing important information
        filename = "test_garbage.pid"
        with open(filename, "w") as f:
            f.write("important!")

        # When I try to start the cli and pass that file as a PID file
        proc = start_cli("tests.test_pidfile:broker", extra_args=["--pid-file", filename])
        proc.wait()

        # Then the process should exit with return code 4
        assert proc.returncode == 4
    finally:
        remove(filename)


@skip_on_windows
def test_cli_with_pidfile_can_be_reloaded(start_cli):
    try:
        # Given that I have a PID file
        filename = "test_reload.pid"

        # When I try to start the cli and pass that file as a PID file
        proc = start_cli("tests.test_pidfile:broker", extra_args=["--pid-file", filename])
        time.sleep(1)

        # And send the proc a HUP signal
        proc.send_signal(signal.SIGHUP)
        time.sleep(5)

        # And then terminate the process
        proc.terminate()
        proc.wait()

        # Then the process should exit with return code 0
        assert proc.returncode == 0
    finally:
        remove(filename)
