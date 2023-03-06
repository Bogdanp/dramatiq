import asyncio
import threading
import time
from concurrent.futures import TimeoutError
from typing import Awaitable, Optional

import dramatiq
from dramatiq.middleware import Middleware

from ..logging import get_logger
from .threading import Interrupt

__all__ = ["AsyncActor", "AsyncMiddleware", "async_actor"]


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

    def run_coroutine(self, coro: Awaitable) -> None:
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
                future.result(timeout=self.INTERRUPT_CHECK_INTERVAL)
            except Interrupt:
                # Asynchronously raised from another thread: cancel the future and
                # reiterate to wait for possible cleanup actions.
                self.loop.call_soon_threadsafe(future.cancel)
            except TimeoutError:
                continue

            break

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

    event_loop_thread: Optional[EventLoopThread] = None

    def __init__(self):
        self.logger = get_logger(__name__, type(self))

    def run_coroutine(self, coro: Awaitable) -> None:
        self.event_loop_thread.run_coroutine(coro)

    def before_worker_boot(self, broker, worker):
        self.event_loop_thread = EventLoopThread(self.logger)
        self.event_loop_thread.start()

        # Monkeypatch the broker to make the event loop thread reachable
        # from an actor or from other middleware.
        broker.run_coroutine = self.event_loop_thread.run_coroutine

    def after_worker_shutdown(self, broker, worker):
        self.event_loop_thread.join()
        self.event_loop_thread = None

        delattr(broker, "run_coroutine")


class AsyncActor(dramatiq.Actor):
    """To configure coroutines as a dramatiq actor.

    Requires AsyncMiddleware to be active.

    Example usage:

    >>> @dramatiq.actor(..., actor_class=AsyncActor)
    ... async def my_task(x):
    ...     print(x)

    Notes:

    The coroutine is scheduled on an event loop that is shared between
    worker threads. See AsyncMiddleware and EventLoopThread.

    This is compatible with ShutdownNotifications ("notify_shutdown") and
    TimeLimit ("time_limit"). Both result in an asyncio.CancelledError raised inside
    the async function. There is currently no way to tell the two apart from
    within the coroutine.
    """

    def __init__(self, fn, *args, **kwargs):
        super().__init__(
            lambda *args, **kwargs: self.broker.run_coroutine(fn(*args, **kwargs)),
            *args,
            **kwargs
        )


def async_actor(awaitable=None, **kwargs):
    if awaitable is not None:
        return dramatiq.actor(awaitable, actor_class=AsyncActor, **kwargs)
    else:

        def wrapper(awaitable):
            return dramatiq.actor(awaitable, actor_class=AsyncActor, **kwargs)

        return wrapper
