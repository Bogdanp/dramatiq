from __future__ import annotations

import time
import urllib.request as request
from threading import Thread

import dramatiq
from dramatiq import Worker
from dramatiq.brokers.stub import StubBroker
from dramatiq.middleware.prometheus import Prometheus


def test_prometheus_middleware_exposes_metrics():
    # Given an instance of the exposition server
    from dramatiq.middleware.prometheus import _run_exposition_server

    thread = Thread(target=_run_exposition_server, daemon=True)
    thread.start()

    # When I give it time to boot up
    time.sleep(1)

    # And I request metrics via HTTP
    with request.urlopen("http://127.0.0.1:9191") as resp:
        # Then the response should be successful
        assert resp.getcode() == 200


def test_prometheus_middleware_delayed_messages_inprogress_returns_to_zero():
    # Given a broker with the Prometheus middleware
    broker = StubBroker()
    prometheus = Prometheus()
    broker.add_middleware(prometheus)
    broker.emit_after("process_boot")
    dramatiq.set_broker(broker)

    # And an actor
    @dramatiq.actor
    def do_work():
        return 42

    # And a running worker
    worker = Worker(broker, worker_threads=1)
    worker.start()
    try:
        # When I send it a delayed message and let it run to completion
        do_work.send_with_options(delay=100)
        broker.join(do_work.queue_name, timeout=5000)
        worker.join()

        # Then the delayed-messages-in-progress gauge should be back to zero
        # for every queue-name label the message passed through.  The message
        # is delayed on the ".DQ" queue but processed on the canonical queue,
        # so the middleware must record both events against the same label or
        # the gauge never settles back to zero.
        gauge = prometheus.inprogress_delayed_messages
        for labels, child in gauge._metrics.items():
            assert child._value.get() == 0, (labels, child._value.get())

        # And the in-memory delayed-message set should not leak.
        assert prometheus.delayed_messages == set()
    finally:
        worker.stop()
        broker.close()
