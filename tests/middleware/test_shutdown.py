import logging
import time
from unittest import mock

import pytest

import remoulade
from remoulade.brokers.stub import StubBroker
from remoulade.middleware import shutdown, threading

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


@mock.patch("remoulade.middleware.shutdown.raise_thread_exception")
def test_shutdown_notifications_worker_shutdown_messages(raise_thread_exception, caplog):
    # capture all messages
    caplog.set_level(logging.NOTSET)

    # Given a middleware with two "threads"
    middleware = shutdown.ShutdownNotifications()
    middleware.notifications = [1, 2]

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
        ("remoulade.middleware.shutdown.ShutdownNotifications", logging.DEBUG, (
            "Sending shutdown notification to worker threads..."
        )),
        ("remoulade.middleware.shutdown.ShutdownNotifications", logging.INFO, (
            "Worker shutdown notification. Raising exception in worker thread 1."
        )),
        ("remoulade.middleware.shutdown.ShutdownNotifications", logging.INFO, (
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
    @remoulade.actor(notify_shutdown=actor_opt)
    def do_work():
        pass

    # And this actor is declared
    stub_broker.declare_actor(do_work)

    # And a message
    message = do_work.message_with_options(notify_shutdown=message_opt)

    # The notification should only be set when expected
    assert middleware.should_notify(do_work, message) == should_notify


@pytest.mark.skipif(not_supported, reason="Threading not supported on this platform.")
def test_shutdown_notifications_are_received(stub_broker, stub_worker):
    # Given that I have a database
    shutdowns, successes = [], []

    # And an actor that handles shutdown interrupts
    @remoulade.actor(notify_shutdown=True, max_retries=0)
    def do_work():
        try:
            for _ in range(10):
                time.sleep(.1)
        except shutdown.Shutdown:
            shutdowns.append(1)
            raise
        successes.append(1)

    # And this actor is declared
    stub_broker.declare_actor(do_work)

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
    @remoulade.actor(max_retries=0)
    def do_work():
        try:
            time.sleep(.2)
        except shutdown.Shutdown:
            shutdowns.append(1)
        else:
            successes.append(1)

    # And this actor is declared
    stub_broker.declare_actor(do_work)

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
    @remoulade.actor(notify_shutdown=True, max_retries=0)
    def do_work(n=10, i=.1):
        try:
            for _ in range(n):
                time.sleep(i)
        except shutdown.Shutdown:
            shutdowns.append(1)
            raise
        successes.append(1)

    # And this actor is declared
    stub_broker.declare_actor(do_work)

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
