from __future__ import annotations

import time
import urllib.request as request
from threading import Thread

from dramatiq.middleware.prometheus import Prometheus, _run_exposition_server


def test_prometheus_middleware_initializes_metrics_on_worker_boot():
    # Given a fresh Prometheus middleware instance
    middleware = Prometheus()

    # When only the worker_boot hook fires, as dramatiq.worker.Worker does on
    # its own, rather than the process_boot hook the dramatiq CLI's forked
    # processes emit before ever constructing a Worker
    middleware.after_worker_boot(broker=None, worker=None)

    # Then its metrics should already be set up and ready to record
    assert middleware.message_durations is not None
    assert middleware.inprogress_messages is not None
    assert middleware.total_messages is not None


def test_prometheus_middleware_exposes_metrics():
    # Given an instance of the exposition server
    thread = Thread(target=_run_exposition_server, daemon=True)
    thread.start()

    # When I give it time to boot up
    time.sleep(1)

    # And I request metrics via HTTP
    with request.urlopen("http://127.0.0.1:9191") as resp:
        # Then the response should be successful
        assert resp.getcode() == 200
