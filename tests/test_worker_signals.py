from __future__ import annotations

import signal
import subprocess
import time

from dramatiq.brokers.stub import StubBroker
from dramatiq.cli import RET_KILLED
from dramatiq.middleware.asyncio import AsyncIO

from .common import skip_on_windows

broker = StubBroker()
broker.add_middleware(AsyncIO())


@skip_on_windows
def test_second_sigterm_kills_a_worker_whose_event_loop_thread_is_running(start_cli):
    # Given a worker process whose AsyncIO middleware runs its event loop thread
    proc = start_cli(
        "tests.test_worker_signals:broker",
        extra_args=["--processes", "1", "--threads", "1"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    for line in proc.stdout:
        if b"Worker process is ready for action" in line:
            break

    # When it gets a second SIGTERM while it is still waiting to stop
    proc.send_signal(signal.SIGTERM)
    time.sleep(0.1)
    proc.send_signal(signal.SIGTERM)

    # Then it is killed, instead of waiting forever on the event loop thread
    try:
        assert proc.wait(timeout=10) == RET_KILLED
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
