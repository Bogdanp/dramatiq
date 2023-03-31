from __future__ import annotations

import asyncio
import functools
import threading
import time
from concurrent.futures import TimeoutError
from typing import TYPE_CHECKING, Awaitable, Callable, Optional, TypeVar

from dramatiq.middleware import Middleware

from ..logging import get_logger
from .threading import Interrupt

if TYPE_CHECKING:
    from typing_extensions import ParamSpec

    P = ParamSpec("P")
else:
    P = TypeVar("P")
R = TypeVar("R")

__all__ = ["AsyncMiddleware", "async_to_sync"]

# the global event loop thread
global_event_loop_thread = None


def get_event_loop_thread() -> "EventLoopThread":
    """Get the global event loop thread.

    If no global broker is set, RuntimeError error will be raised.

    Returns:
      Broker: The global EventLoopThread.
    """
    global global_event_loop_thread
    if global_event_loop_thread is None:
        raise RuntimeError(
            "The usage of asyncio in dramatiq requires the AsyncMiddleware "
            "to be configured."
        )
    return global_event_loop_thread


def set_event_loop_thread(event_loop_thread: Optional["EventLoopThread"]) -> None:
    global global_event_loop_thread
    global_event_loop_thread = event_loop_thread


def async_to_sync(async_fn: Callable[P, Awaitable[R]]) -> Callable[P, R]:
    """Wrap an 'async def' function to make it synchronous."""
    # assert presence of event loop thread:
    get_event_loop_thread()

    @functools.wraps(async_fn)
    def wrapper(*args, **kwargs) -> R:
        return get_event_loop_thread().run_coroutine(async_fn(*args, **kwargs))

    return wrapper


class EventLoopThread(threading.Thread):
    """A thread that runs an asyncio event loop.

    The method 'run_coroutine' should be used to run coroutines from a
    synchronous context.
    """

    # seconds to wait for the event loop to start
    EVENT_LOOP_START_TIMEOUT = 0.1
    # interval (seconds) to reactivate the worker thread and check
    # for interrupts
    INTERRUPT_CHECK_INTERVAL = 1.0

    loop: Optional[asyncio.AbstractEventLoop] = None

    def __init__(self, logger):
        self.logger = logger
        super().__init__(target=self._start_event_loop)

    def _start_event_loop(self):
        """This method should run in the thread"""
        self.logger.info("Starting the event loop...")

        self.loop = asyncio.new_event_loop()
        try:
            self.loop.run_forever()
        finally:
            self.loop.close()

    def _stop_event_loop(self):
        """This method should run outside of the thread"""
        if self.loop is not None and self.loop.is_running():
            self.logger.info("Stopping the event loop...")
            self.loop.call_soon_threadsafe(self.loop.stop)

    def run_coroutine(self, coro: Awaitable[R]) -> R:
        """To be called from outside the thread

        Blocks until the coroutine is finished.
        """
        if self.loop is None or not self.loop.is_running():
            raise RuntimeError("The event loop is not running")
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        while True:
            try:
                # Use a timeout to be able to catch asynchronously raised dramatiq
                # exceptions (Interrupt).
                return future.result(timeout=self.INTERRUPT_CHECK_INTERVAL)
            except Interrupt:
                # Asynchronously raised from another thread: cancel the future and
                # reiterate to wait for possible cleanup actions.
                self.loop.call_soon_threadsafe(future.cancel)
            except TimeoutError:
                continue

    def start(self, *args, **kwargs):
        super().start(*args, **kwargs)
        time.sleep(self.EVENT_LOOP_START_TIMEOUT)
        if self.loop is None or not self.loop.is_running():
            raise RuntimeError("The event loop failed to start")
        self.logger.info("Event loop is running.")

    def join(self, *args, **kwargs):
        self._stop_event_loop()
        return super().join(*args, **kwargs)


class AsyncMiddleware(Middleware):
    """This middleware manages the event loop thread.

    This thread is used to schedule coroutines on from the worker threads.
    """

    def __init__(self):
        self.logger = get_logger(__name__, type(self))

    def before_worker_boot(self, broker, worker):
        event_loop_thread = EventLoopThread(self.logger)
        event_loop_thread.start()

        set_event_loop_thread(event_loop_thread)

    def after_worker_shutdown(self, broker, worker):
        get_event_loop_thread().join()
        set_event_loop_thread(None)
