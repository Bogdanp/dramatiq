import logging
import time
from threading import get_ident as get_thread_ident
from unittest import mock

import pytest
from gevent.timeout import _FakeTimer
from greenlet import getcurrent

import dramatiq
from dramatiq.brokers.stub import StubBroker
from dramatiq.middleware import time_limit, threading

from ..common import skip_with_gevent, skip_without_gevent


not_supported = threading.current_platform not in threading.supported_platforms


def test_time_limit_platform_not_supported(recwarn, monkeypatch):
    # monkeypatch fake platform to test logging.
    monkeypatch.setattr(time_limit, "current_platform", "not supported")

    # Given a broker configured with time limits
    broker = StubBroker(middleware=[time_limit.TimeLimit()])

    # When the process boots
    broker.emit_after("process_boot")

    # A platform support warning is issued
    assert len(recwarn) == 1
    assert str(recwarn[0].message) == ("TimeLimit cannot kill threads "
                                       "on your current platform ('not supported').")


@skip_with_gevent
@mock.patch("dramatiq.middleware.time_limit.raise_thread_exception")
def test_time_limit_exceeded_worker_messages(raise_thread_exception, caplog):
    # capture all messages
    caplog.set_level(logging.NOTSET)

    current_time = time.monotonic()

    # Given a middleware with two "threads" that have exceeded their deadlines
    # and one "thread" that has not
    middleware = time_limit.TimeLimit()
    middleware.deadlines = {
        1: current_time - 2, 2: current_time - 1, 3: current_time + 50000}

    # When the time limit handler is triggered
    middleware._handle()

    # TimeLimitExceeded interrupts are raised in two of the threads
    raise_thread_exception.assert_has_calls([
        mock.call(1, time_limit.TimeLimitExceeded),
        mock.call(2, time_limit.TimeLimitExceeded),
    ])

    # And TimeLimitExceeded warnings are logged for those threads.
    assert len(caplog.record_tuples) == 2
    assert caplog.record_tuples == [
        ("dramatiq.middleware.time_limit.TimeLimit", logging.WARNING, (
            "Time limit exceeded. Raising exception in worker thread 1."
        )),
        ("dramatiq.middleware.time_limit.TimeLimit", logging.WARNING, (
            "Time limit exceeded. Raising exception in worker thread 2."
        )),
    ]


@skip_without_gevent
@mock.patch("dramatiq.middleware.time_limit.Timeout._on_expiration")
def test_time_limit_exceeded_gevent_worker_messages(on_expiration, caplog):
    # capture all messages
    caplog.set_level(logging.NOTSET)

    # Given a time limit middleware instance and three gevent timers with
    # two short time limits and one long time limit
    middleware = time_limit.TimeLimit()
    timer_1 = time_limit.GeventTimeout(
        seconds=.01, thread_id=1, logger=middleware.logger,
        exception=time_limit.TimeLimitExceeded)
    timer_2 = time_limit.GeventTimeout(
        seconds=.02, thread_id=2, logger=middleware.logger,
        exception=time_limit.TimeLimitExceeded)
    timer_3 = time_limit.GeventTimeout(
        seconds=10, thread_id=3, logger=middleware.logger,
        exception=time_limit.TimeLimitExceeded)

    # When the timers are all started
    timer_1.start()
    timer_2.start()
    timer_3.start()

    # And enough time passes for two of the time limits to be exceeded
    time.sleep(.1)

    # I expect TimeLimitExceeded exceptions to be used in the on_expiration
    # callbacks for those timers
    current_greenlet = getcurrent()
    assert on_expiration.assert_has_calls
    on_expiration.assert_has_calls([
        mock.call(current_greenlet, time_limit.TimeLimitExceeded),
        mock.call(current_greenlet, time_limit.TimeLimitExceeded),
    ])

    # And I expect TimeLimitExceeded warnings to be logged for the expected
    # threads.
    assert len(caplog.record_tuples) == 2
    assert caplog.record_tuples == [
        ("dramatiq.middleware.time_limit.TimeLimit", logging.WARNING, (
            "Time limit exceeded. Raising exception in worker thread 1."
        )),
        ("dramatiq.middleware.time_limit.TimeLimit", logging.WARNING, (
            "Time limit exceeded. Raising exception in worker thread 2."
        )),
    ]
    timer_1.close()
    timer_2.close()
    timer_3.close()


@pytest.mark.skipif(not_supported, reason="Threading not supported on this platform.")
def test_time_limits_are_handled(stub_broker, stub_worker):
    # Given that I have a database
    time_limits_exceeded, successes = [], []

    # And an actor that handles time limit exceeded interrupts
    @dramatiq.actor(time_limit=10, max_retries=0)
    def do_work():
        try:
            for _ in range(20):
                time.sleep(.1)
        except time_limit.TimeLimitExceeded:
            time_limits_exceeded.append(1)
            raise
        successes.append(1)

    # If I send it a message
    do_work.send()

    # Then join on the queue
    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # I expect the time limit to have been exceeded
    assert sum(time_limits_exceeded) == 1
    assert sum(successes) == 0


@skip_with_gevent
@pytest.mark.parametrize("message_opt, actor_opt, expected_deadline", [
    (None, None, 600), (None, 2000, 2), (1000, None, 1), (1000, 2000, 1),
    (2000, 1000, 2), (1200, None, 1.2), (None, 1200, 1.2),
    (float("inf"), 2000, float("inf")), (None, float("inf"), float("inf")),
])
@mock.patch("dramatiq.middleware.time_limit.monotonic", return_value=0)
def test_time_limits_are_tracked(_mock_monotonic, message_opt, actor_opt, expected_deadline):
    # Given that I have a time limit middleware instance
    middleware = time_limit.TimeLimit()

    # And a mock actor and mock message with the specified options
    actor_options = {} if actor_opt is None else {"time_limit": actor_opt}
    message_options = {} if message_opt is None else {"time_limit": message_opt}
    mock_actor = mock.Mock(options=actor_options)
    mock_broker = mock.Mock(get_actor=lambda _actor_name: mock_actor)
    mock_message = mock.Mock(options=message_options)

    # When I trigger before_process_message for the middleware
    middleware.before_process_message(mock_broker, mock_message)

    # The middleware sets the expected deadline for the thread.
    thread_id = get_thread_ident()
    assert len(middleware.deadlines) == 1
    assert middleware.deadlines[thread_id] == expected_deadline


@skip_without_gevent
@pytest.mark.parametrize("message_opt, actor_opt, expected_seconds", [
    (None, None, 600), (None, 2000, 2), (1000, None, 1), (1000, 2000, 1),
    (2000, 1000, 2), (1200, None, 1.2), (None, 1200, 1.2),
    (float("inf"), 2000, None), (None, float("inf"), None),
])
def test_time_limits_are_tracked_with_gevent(message_opt, actor_opt, expected_seconds):
    # Given that I have a time limit middleware instance
    middleware = time_limit.TimeLimit()

    # And a mock actor and mock message with the specified options
    actor_options = {} if actor_opt is None else {"time_limit": actor_opt}
    message_options = {} if message_opt is None else {"time_limit": message_opt}
    mock_actor = mock.Mock(options=actor_options)
    mock_broker = mock.Mock(get_actor=lambda _actor_name: mock_actor)
    mock_message = mock.Mock(options=message_options)

    # When I trigger before_process_message for the middleware
    middleware.before_process_message(mock_broker, mock_message)

    # I expect the middleware to have set gevent timeouts with the expected
    # number of seconds
    thread_id = get_thread_ident()
    assert len(middleware.gevent_timers) == 1
    assert middleware.gevent_timers[thread_id].seconds == expected_seconds
    # And the gevent timer is faked if the expected_seconds is None.
    if expected_seconds is None:
        assert isinstance(middleware.gevent_timers[thread_id].timer, type(_FakeTimer))

    middleware.gevent_timers[thread_id].close()


@skip_with_gevent
def test_time_limits_are_cleaned_up_after_processing():
    # Given that I have a time limit middleware instance
    middleware = time_limit.TimeLimit()

    # With a deadline set for a thread
    thread_id = get_thread_ident()
    middleware.deadlines[thread_id] = 1000

    # After a message is processed by the thread, the deadline for the thread
    # is set to None.
    middleware.after_process_message(mock.Mock(), mock.Mock())
    assert middleware.deadlines[thread_id] is None


@skip_with_gevent
def test_time_limits_are_cleaned_up_after_skipping():
    # Given that I have a time limit middleware instance
    middleware = time_limit.TimeLimit()

    # With a deadline set for a thread
    thread_id = get_thread_ident()
    middleware.deadlines[thread_id] = 1000

    # After a message is skipped by the thread, the deadline for the thread
    # is set to None.
    middleware.after_skip_message(mock.Mock(), mock.Mock())
    assert middleware.deadlines[thread_id] is None


@skip_without_gevent
def test_time_limits_are_cleaned_up_after_processing_gevent():
    # Given that I have a time limit middleware instance
    middleware = time_limit.TimeLimit()

    # With a mock gevent timeout set for a thread
    thread_id = get_thread_ident()
    mock_close = mock.Mock()
    mock_timeout = mock.Mock(close=mock_close)
    middleware.gevent_timers[thread_id] = mock_timeout

    # After a message is processed by the thread, the timeout for the thread
    # is closed and set to None.
    middleware.after_process_message(mock.Mock(), mock.Mock())
    assert mock_close.called
    assert middleware.gevent_timers[thread_id] is None


@skip_without_gevent
def test_time_limits_are_cleaned_up_after_skipping_gevent():
    # Given that I have a time limit middleware instance
    middleware = time_limit.TimeLimit()

    # With a mock gevent timeout set for a thread
    thread_id = get_thread_ident()
    mock_close = mock.Mock()
    mock_timeout = mock.Mock(close=mock_close)
    middleware.gevent_timers[thread_id] = mock_timeout

    # After a message is processed by the thread, the timeout for the thread
    # is closed and set to None.
    middleware.after_skip_message(mock.Mock(), mock.Mock())
    assert mock_close.called
    assert middleware.gevent_timers[thread_id] is None
