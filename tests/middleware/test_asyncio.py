import asyncio
import threading
from unittest import mock

import pytest

from dramatiq.middleware.asyncio import (
    AsyncMiddleware,
    EventLoopThread,
    async_to_sync,
    get_event_loop_thread,
    set_event_loop_thread,
)


@pytest.fixture
def started_thread():
    thread = EventLoopThread(logger=mock.Mock())
    thread.start()
    set_event_loop_thread(thread)
    yield thread
    thread.join()
    set_event_loop_thread(None)


@pytest.fixture
def logger():
    return mock.Mock()


def test_event_loop_thread_start():
    try:
        thread = EventLoopThread(logger=mock.Mock())
        thread.start()
        assert isinstance(thread.loop, asyncio.BaseEventLoop)
        assert thread.loop.is_running()
    finally:
        thread.join()


def test_event_loop_thread_run_coroutine(started_thread: EventLoopThread):
    result = {}

    async def get_thread_id():
        return threading.get_ident()

    result = started_thread.run_coroutine(get_thread_id())

    # the coroutine executed in the event loop thread
    assert result == started_thread.ident


def test_event_loop_thread_run_coroutine_exception(started_thread: EventLoopThread):
    async def raise_error():
        raise TypeError("bla")

    coro = raise_error()

    with pytest.raises(TypeError, match="bla"):
        started_thread.run_coroutine(coro)


@mock.patch("dramatiq.middleware.asyncio.EventLoopThread")
def test_async_middleware_before_worker_boot(EventLoopThreadMock):
    middleware = AsyncMiddleware()

    try:
        middleware.before_worker_boot(None, None)

        assert get_event_loop_thread() is EventLoopThreadMock.return_value

        EventLoopThreadMock.assert_called_once_with(middleware.logger)
        EventLoopThreadMock().start.assert_called_once_with()
    finally:
        set_event_loop_thread(None)


def test_async_middleware_after_worker_shutdown():
    middleware = AsyncMiddleware()
    event_loop_thread = mock.Mock()

    set_event_loop_thread(event_loop_thread)

    try:
        middleware.after_worker_shutdown(None, None)

        with pytest.raises(RuntimeError):
            get_event_loop_thread()

        event_loop_thread.join.assert_called_once_with()
    finally:
        set_event_loop_thread(None)


async def async_fn(value: int = 2) -> int:
    return value + 1


@mock.patch("dramatiq.middleware.asyncio.get_event_loop_thread")
def test_async_to_sync(get_event_loop_thread_mocked):
    thread = get_event_loop_thread_mocked()

    fn = async_to_sync(async_fn)
    actual = fn(2)
    thread.run_coroutine.assert_called_once()
    assert actual is thread.run_coroutine()


@pytest.mark.usefixtures("started_thread")
def test_async_to_sync_with_actual_thread(started_thread):
    fn = async_to_sync(async_fn)

    assert fn(2) == 3


def test_async_to_sync_no_thread():
    with pytest.raises(RuntimeError):
        async_to_sync(async_fn)
