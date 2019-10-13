import time
import urllib.request as request
from threading import Thread

from dramatiq.middleware.prometheus import _run_exposition_server


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
