import multiprocessing
import os
import tempfile
import time
import urllib.request as request
from threading import Thread

import pytest

from dramatiq.middleware.prometheus import _prom_db_path, _run_exposition_server


def test_prometheus_middleware_exposes_metrics(tmp_path, monkeypatch):
    # Given Prometheus multi-proc DB dir set up
    prom_db_path = tmp_path / "dramatiq-prometheus"
    prom_db_path.mkdir()
    monkeypatch.setenv("DRAMATIQ_PROM_DB", str(prom_db_path))

    # And given an instance of the exposition server
    thread = Thread(target=_run_exposition_server, daemon=True)
    thread.start()

    # And I request metrics via HTTP
    # use 5 tries, with 1 second delay each
    for try_num in range(5):
        time.sleep(1)
        try:
            with request.urlopen("http://127.0.0.1:9191") as resp:
                # Then the response should be successful
                assert resp.getcode() == 200
                break
        except OSError:
            if try_num >= 4:
                raise


def test_prometheus_db_path_override(monkeypatch):
    # Given Prometheus DB path override through ENV var
    monkeypatch.setenv("DRAMATIQ_PROM_DB", "/foo/bar")
    # When requesting DB path
    db_path, is_external = _prom_db_path()
    # Then the path should be overridden and is_external flag set
    assert db_path == "/foo/bar"
    assert is_external is True


@pytest.fixture
def default_db_path():
    return f"{tempfile.gettempdir()}/dramatiq-prometheus-{os.getpid()}"


def test_prometheus_db_path_current_pid(default_db_path):
    # When requesting DB path from a process without parents
    db_path, is_external = _prom_db_path()
    # Then DB path should use the current PID, and is_external flag not set
    assert db_path == default_db_path
    assert is_external is False


def test_prometheus_db_path_parent_pid(default_db_path):
    # When requesting DB path from within a subprocess
    with multiprocessing.Pool(1) as pool:
        db_path, is_external = pool.apply(_prom_db_path)
    # Then DB path should still use the current PID, and is_external flag not set
    assert db_path == default_db_path
    assert is_external is False
