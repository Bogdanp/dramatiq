import logging
import time
from threading import Thread

import pytest

from dramatiq import threading

not_supported = threading.current_platform not in threading.supported_platforms


@pytest.mark.skipif(not_supported, reason="Threading not supported on this platform.")
@pytest.mark.skipif(threading.is_gevent_active(), reason="Thread exceptions not supported with gevent.")
def test_raise_thread_exception():
    # Given that I have a database
    caught = []

    # And a function that waits for an interrupt
    def work():
        try:
            for _ in range(10):
                time.sleep(.1)
        except threading.Interrupt:
            caught.append(1)

    # When I start the thread
    t = Thread(target=work)
    t.start()
    time.sleep(.1)

    # And raise the interrupt and join on the thread
    threading.raise_thread_exception(t.ident, threading.Interrupt)
    t.join()

    # I expect the interrupt to have been caught
    assert sum(caught) == 1


@pytest.mark.skipif(not_supported, reason="Threading not supported on this platform.")
@pytest.mark.skipif(threading.is_gevent_active(), reason="Thread exceptions not supported with gevent.")
def test_raise_thread_exception_on_nonexistent_thread(caplog):
    # When an interrupt is raised on a nonexistent thread
    thread_id = 2 ** 31 - 1
    threading.raise_thread_exception(thread_id, threading.Interrupt)

    # I expect a 'failed to set exception' critical message to be logged
    expected_message = "Failed to set exception (Interrupt) in thread %d." % thread_id
    assert caplog.record_tuples == [
        ("dramatiq.threading", logging.CRITICAL, expected_message),
    ]


def test_raise_thread_exception_unsupported_platform(caplog, monkeypatch):
    # monkeypatch fake platform to test logging.
    monkeypatch.setattr(threading, "current_platform", "not supported")

    # When raising a thread exception on an unsupported platform
    threading.raise_thread_exception(1, threading.Interrupt)

    # I expect a 'platform not supported' critical message to be logged
    assert caplog.record_tuples == [
        ("dramatiq.threading", logging.CRITICAL, (
            "Setting thread exceptions (Interrupt) is not supported "
            "for your current platform ('not supported')."
        )),
    ]
