from __future__ import annotations

import asyncio
import inspect
from threading import Event, Thread, get_ident
from unittest import mock

import pytest

from dramatiq import actor, threading
from dramatiq.asyncio import (
    EventLoopThread,
    async_to_sync,
    get_event_loop_thread,
    set_event_loop_thread,
)
from dramatiq.logging import get_logger
from dramatiq.middleware import CurrentMessage
from dramatiq.middleware.asyncio import AsyncIO

from ..common import worker


@pytest.fixture
def started_thread():
    thread = EventLoopThread(logger=get_logger(__name__))
    thread.start()
    set_event_loop_thread(thread)
    yield thread
    thread.stop()
    set_event_loop_thread(None)


def test_event_loop_thread_start():
    thread = EventLoopThread(logger=get_logger(__name__))
    try:
        thread.start(timeout=1.0)
        assert isinstance(thread.loop, asyncio.BaseEventLoop)
        assert thread.loop.is_running()
    finally:
        thread.stop()
        thread.join()


def test_event_loop_thread_start_timeout():
    thread = EventLoopThread(logger=get_logger(__name__))
    loop_mock = mock.Mock()
    # Store the original thread loop and replace it with a mock.
    original_loop = thread.loop
    thread.loop = loop_mock
    with pytest.raises(RuntimeError, match="Event loop failed to start"):
        thread.start(timeout=0.1)
    # Close the original event loop to prevent a ResourceWarning.
    original_loop.close()


def test_event_loop_thread_run_coroutine(started_thread: EventLoopThread):
    result = {}

    async def get_thread_id():
        return get_ident()

    result = started_thread.run_coroutine(get_thread_id())

    # the coroutine executed in the event loop thread
    assert result == started_thread.ident


def test_event_loop_thread_run_coroutine_exception(started_thread: EventLoopThread):
    async def raise_actual_error():
        raise TypeError("bla")

    async def raise_error():
        await raise_actual_error()

    coro = raise_error()

    with pytest.raises(TypeError, match="bla") as e:
        started_thread.run_coroutine(coro)

    # the error has the correct traceback
    assert e.traceback[-2].name == "raise_error"
    assert e.traceback[-1].name == "raise_actual_error"


def test_event_loop_thread_run_coroutine_timeout_exception(started_thread: EventLoopThread):
    """Test that TimeoutError in coroutine doesn't lead to infinite loop.

    Regression test for https://github.com/Bogdanp/dramatiq/issues/791
    """

    async def raise_actual_error():
        raise TimeoutError("something took too long")

    async def raise_error():
        await raise_actual_error()

    coro = raise_error()

    with pytest.raises(TimeoutError, match="something took too long"):
        started_thread.run_coroutine(coro)


@pytest.mark.skipif(
    threading.current_platform not in threading.supported_platforms,
    reason="Threading not supported on this platform.",
)
@pytest.mark.skipif(threading.is_gevent_active(), reason="Thread exceptions not supported with gevent.")
def test_event_loop_thread_run_coroutine_interrupted(started_thread: EventLoopThread):
    """Test that when EventLoopThread.run_coroutine() is interrupted,
    the coroutine cleanup is allowed to run.

    Note: in this test the main test thread calls EventLoopThread.run_coroutine()
    AND is interrupted with a threading.Interrupt exception.
    This simulates how the Worker threads call EventLoopThread.run_coroutine()
    and are interrupted by TimeLimit/Shutdown middleware.
    """
    side_effect_target = {"cleanup": False}
    ready_for_interrupt = Event()

    # Set up a thread to interrupt the "worker thread" (i.e. the main test thread)
    # This simulates TimeLimit/Shutdown middleware.
    def interrupter(*, worker_thread_id: int):
        ready_for_interrupt.wait()
        threading.raise_thread_exception(worker_thread_id, threading.Interrupt)

    test_thread_id = get_ident()
    interrupter_thread = Thread(target=interrupter, kwargs={"worker_thread_id": test_thread_id})
    interrupter_thread.start()

    # This will be canceled when the interrupt happens.
    # This cleanup code in the 'finally' block should run.
    async def sleeper():
        try:
            ready_for_interrupt.set()
            while True:
                await asyncio.sleep(0.01)
        finally:
            await asyncio.sleep(0.01)
            side_effect_target["cleanup"] = True

    with pytest.raises(threading.Interrupt):
        started_thread.run_coroutine(sleeper())

    # Assert cleanup code was run
    assert side_effect_target["cleanup"]

    # ensure interrupter thread has finished.
    interrupter_thread.join(timeout=1)
    assert not interrupter_thread.is_alive()


@mock.patch("dramatiq.middleware.asyncio.EventLoopThread")
def test_async_middleware_before_worker_boot(EventLoopThreadMock):
    middleware = AsyncIO()
    try:
        middleware.before_worker_boot(None, None)
        assert get_event_loop_thread() is EventLoopThreadMock.return_value
    finally:
        set_event_loop_thread(None)


def test_async_middleware_after_worker_shutdown():
    middleware = AsyncIO()
    event_loop_thread = mock.Mock()
    set_event_loop_thread(event_loop_thread)
    try:
        middleware.after_worker_shutdown(None, None)
        assert get_event_loop_thread() is None
    finally:
        set_event_loop_thread(None)


@mock.patch("dramatiq.asyncio.get_event_loop_thread")
def test_async_to_sync(get_event_loop_thread_mocked):
    mock_async_function = mock.Mock()
    thread = get_event_loop_thread_mocked()
    set_event_loop_thread(thread)

    # Check that a callable sync function is returned.
    fn = async_to_sync(mock_async_function)
    assert callable(fn) and inspect.isfunction(fn) and not inspect.iscoroutinefunction(fn)

    # Call the sync function
    actual = fn(2, foo="bar")
    try:
        # Check that the (kw)args were passed through to the async function.
        mock_async_function.assert_called_once_with(2, foo="bar")

        # Check that run_coroutine was called once with return value from async function
        thread.run_coroutine.assert_called_once_with(mock_async_function.return_value)
        assert actual is thread.run_coroutine.return_value

    finally:
        set_event_loop_thread(None)


async def async_fn(value: int = 2) -> int:
    return value + 1


def test_async_to_sync_with_actual_thread(started_thread):
    assert async_to_sync(async_fn)(2) == 3


def test_async_to_sync_no_thread():
    with pytest.raises(RuntimeError):
        async_to_sync(async_fn)(2)


def test_anyio_currrent_message_middleware_exposes_the_current_message(stub_broker):
    # Given that I have a CurrentMessage middleware
    stub_broker.add_middleware(AsyncIO())
    stub_broker.add_middleware(CurrentMessage())

    with worker(stub_broker, worker_timeout=100, worker_threads=1):
        # And an actor that accesses the current message
        sent_messages = []
        received_messages = []

        @actor
        async def accessor(x):
            message_proxy = CurrentMessage.get_current_message()
            received_messages.append(message_proxy._message)

        # When I send it a couple messages
        sent_messages.append(accessor.send(1))
        sent_messages.append(accessor.send(2))

        # And wait for it to finish its work
        stub_broker.join(accessor.queue_name)

        # Then the sent messages and the received messages should be the same
        assert sorted(sent_messages) == sorted(received_messages)

        # When I try to access the current message from a non-worker thread
        # Then I should get back None
        assert CurrentMessage.get_current_message() is None
