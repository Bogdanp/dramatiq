from __future__ import annotations

from ..asyncio import EventLoopThread, get_event_loop_thread, set_event_loop_thread
from ..logging import get_logger
from . import Middleware


class AsyncIO(Middleware):
    """This middleware manages the event loop thread for async actors.
    """

    def __init__(self):
        self.logger = get_logger(__name__, type(self))

    def before_worker_boot(self, broker, worker):
        event_loop_thread = EventLoopThread(self.logger)
        event_loop_thread.start(timeout=1.0)
        set_event_loop_thread(event_loop_thread)

    def after_worker_shutdown(self, broker, worker):
        event_loop_thread = get_event_loop_thread()
        event_loop_thread.stop()
        event_loop_thread.join()
        set_event_loop_thread(None)
