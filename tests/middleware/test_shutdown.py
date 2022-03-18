import logging
import time
from unittest import mock

import gevent
import pytest

import dramatiq
from dramatiq.brokers.stub import StubBroker
from dramatiq.middleware import shutdown, threading

from ..common import skip_with_gevent, skip_without_gevent

not_supported = threading.current_platform not in threading.supported_platforms


def test_shutdown_notifications_platform_not_supported(recwarn, monkeypatch):
    # monkeypatch fake platform to test logging.
    monkeypatch.setattr(shutdown, "current_platform", "not supported")

    # Given a broker configured with the shutdown notifier
    broker = StubBroker(middleware=[shutdown.ShutdownNotifications()])

    # When the process boots
    broker.emit_after("process_boot")

    # A platform support warning is issued
    assert len(recwarn) == 1
    assert str(recwarn[0].message) == ("ShutdownNotifications cannot kill threads "
                                       "on your current platform ('not supported').")


@skip_with_gevent
@mock.patch("dramatiq.middleware.shutdown.raise_thread_exception")
def test_shutdown_notifications_worker_shutdown_messages(raise_thread_exception, caplog):
    # capture all messages
    caplog.set_level(logging.NOTSET)

    # Given a middleware with two "threads"
    middleware = shutdown.ShutdownNotifications()
    middleware.manager.notifications = [1, 2]

    # Given a broker configured with the shutdown notifier
    broker = StubBroker(middleware=[middleware])

    # When the worker is shutdown
    broker.emit_before("worker_shutdown", None)

    # Shutdown interrupts are raised in both threads
    raise_thread_exception.assert_has_calls([
        mock.call(1, shutdown.Shutdown),
        mock.call(2, shutdown.Shutdown),
    ])

    # And shutdown notifications are logged
    assert len(caplog.record_tuples) == 3
    assert caplog.record_tuples == [
        ("dramatiq.middleware.shutdown.ShutdownNotifications", logging.DEBUG, (
            "Sending shutdown notification to worker threads..."
        )),
        ("dramatiq.middleware.shutdown.ShutdownNotifications", logging.INFO, (
            "Worker shutdown notification. Raising exception in worker thread 1."
        )),
        ("dramatiq.middleware.shutdown.ShutdownNotifications", logging.INFO, (
            "Worker shutdown notification. Raising exception in worker thread 2."
        )),
    ]


@skip_without_gevent
def test_shutdown_notifications_gevent_worker_shutdown_messages(caplog):
    # capture all messages
    caplog.set_level(logging.NOTSET)

    # Given a middleware with two threads
    middleware = shutdown.ShutdownNotifications()
    greenlet_1 = gevent.spawn()
    greenlet_2 = gevent.spawn()
    middleware.manager.notification_greenlets = [(1, greenlet_1), (2, greenlet_2)]

    # Given a broker configured with the shutdown notifier
    broker = StubBroker(middleware=[middleware])

    # When the worker is shutdown
    broker.emit_before("worker_shutdown", None)

    # Shutdown interrupts are raised in both threads
    assert isinstance(greenlet_1.exception, shutdown.Shutdown)
    assert isinstance(greenlet_2.exception, shutdown.Shutdown)

    # And shutdown notifications are logged
    assert len(caplog.record_tuples) == 3
    assert caplog.record_tuples == [
        ("dramatiq.middleware.shutdown.ShutdownNotifications", logging.DEBUG, (
            "Sending shutdown notification to worker threads..."
        )),
        ("dramatiq.middleware.shutdown.ShutdownNotifications", logging.INFO, (
            "Worker shutdown notification. Raising exception in worker thread 1."
        )),
        ("dramatiq.middleware.shutdown.ShutdownNotifications", logging.INFO, (
            "Worker shutdown notification. Raising exception in worker thread 2."
        )),
    ]


@pytest.mark.parametrize("actor_opt, message_opt, should_notify", [
    (True,  True, True), (True,  False, False), (True,  None, True),   # noqa: E241
    (False, True, True), (False, False, False), (False, None, False),  # noqa: E241
    (None,  True, True), (None,  False, False), (None,  None, False),  # noqa: E241
])
def test_shutdown_notifications_options(stub_broker, actor_opt, message_opt, should_notify):
    # Given the shutdown notifications middleware
    middleware = shutdown.ShutdownNotifications()

    # And an actor
    @dramatiq.actor(notify_shutdown=actor_opt)
    def do_work():
        pass

    # And a message
    message = do_work.message_with_options(notify_shutdown=message_opt)

    # The notification should only be set when expected
    assert middleware.should_notify(do_work, message) == should_notify


@pytest.mark.skipif(not_supported, reason="Threading not supported on this platform.")
def test_shutdown_notifications_are_received(stub_broker, stub_worker):
    # Given that I have a database
    shutdowns, successes = [], []

    # And an actor that handles shutdown interrupts
    @dramatiq.actor(notify_shutdown=True, max_retries=0)
    def do_work():
        try:
            for _ in range(10):
                time.sleep(.1)
        except shutdown.Shutdown:
            shutdowns.append(1)
            raise
        successes.append(1)

    # If I send it a message
    do_work.send()

    # Then wait and signal the worker to terminate
    time.sleep(.1)
    stub_worker.stop()

    # Then join on the queue
    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # I expect it to shutdown
    assert sum(shutdowns) == 1
    assert sum(successes) == 0


@pytest.mark.skipif(not_supported, reason="Threading not supported on this platform.")
def test_shutdown_notifications_can_be_ignored(stub_broker, stub_worker):
    # Given that I have a database
    shutdowns, successes = [], []

    # And an actor
    @dramatiq.actor(max_retries=0)
    def do_work():
        try:
            time.sleep(.2)
        except shutdown.Shutdown:
            shutdowns.append(1)
        else:
            successes.append(1)

    # If I send it a message
    do_work.send()

    # Then wait and signal the worker to terminate
    time.sleep(.1)
    stub_worker.stop()

    # Then join on the queue
    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # I expect success
    assert sum(shutdowns) == 0
    assert sum(successes) == 1


@pytest.mark.skipif(not_supported, reason="Threading not supported on this platform.")
def test_shutdown_notifications_dont_notify_completed_threads(stub_broker, stub_worker):
    # Given that I have a database
    shutdowns, successes = [], []

    # And an actor that handles shutdown interrupts
    @dramatiq.actor(notify_shutdown=True, max_retries=0)
    def do_work(n=10, i=.1):
        try:
            for _ in range(n):
                time.sleep(i)
        except shutdown.Shutdown:
            shutdowns.append(1)
            raise
        successes.append(1)

    # If I send it two message of different execution times
    do_work.send(n=1)
    do_work.send(n=10)

    # Then wait for one message to complete
    time.sleep(.5)

    # Then signal the worker to terminate
    stub_worker.stop()

    # Then join on the queue
    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # I expect only one success and one shutdown
    assert sum(shutdowns) == 1
    assert sum(successes) == 1
