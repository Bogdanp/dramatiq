import urllib.request as request
from time import sleep

import pytest

from remoulade.brokers.stub import StubBroker

prometheus = pytest.importorskip("remoulade.middleware.prometheus")


def test_prometheus_middleware_exposes_metrics():
    try:
        # Given a broker
        broker = StubBroker()

        # And an instance of the prometheus middleware
        prom = prometheus.Prometheus()
        prom.after_process_boot(broker)

        # If I wait for the server to start
        sleep(0.01)

        # When I request metrics via HTTP
        with request.urlopen("http://127.0.0.1:9191") as resp:
            # Then the response should be successful
            assert resp.getcode() == 200
    finally:
        prom.after_worker_shutdown(broker, None)
