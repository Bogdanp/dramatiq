# This file is a part of Dramatiq.
#
# Copyright (C) 2017,2018 CLEARTYPE SRL <bogdan@cleartype.io>
#
# Dramatiq is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# Dramatiq is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import annotations

import threading
import warnings
from threading import Thread
from time import monotonic, sleep
from typing import TYPE_CHECKING, Optional, Union

from ..logging import get_logger
from .middleware import Middleware
from .threading import (
    Interrupt,
    current_platform,
    is_gevent_active,
    raise_thread_exception,
    supported_platforms,
)

if TYPE_CHECKING:
    import gevent


class TimeLimitExceeded(Interrupt):
    """Exception used to interrupt worker threads when actors exceed
    their time limits.
    """


class TimeLimit(Middleware):
    """Middleware that cancels actors that run for too long.
    Currently, this is only available on CPython.

    Note:
      This works by setting an async exception in the worker thread
      that runs the actor.  This means that the exception will only get
      called the next time that thread acquires the GIL.  Concretely,
      this means that this middleware can't cancel system calls.

    Parameters:
      time_limit(float): The maximum number of milliseconds actors may
        run for. Use `float("inf")` to avoid setting a timeout for the
        actor.
        Defaults to 10 minutes (600,000 milliseconds).
      interval(int): The interval (in milliseconds) with which to
        check for actors that have exceeded the limit. This does not take
        effect when using gevent because the timers are managed by gevent.
        Defaults to 1 second (1,000 milliseconds).
    """

    def __init__(self, *, time_limit: float = 600000, interval: int = 1000) -> None:
        self.logger = get_logger(__name__, type(self))
        self.time_limit = time_limit

        self.manager: Union[_GeventTimeoutManager, _CtypesTimeoutManager]
        if is_gevent_active():
            self.manager = _GeventTimeoutManager(logger=self.logger)
        else:
            self.manager = _CtypesTimeoutManager(interval, logger=self.logger)

    @property
    def actor_options(self):
        return {"time_limit"}

    def after_process_boot(self, broker):
        if is_gevent_active() or current_platform in supported_platforms:
            self.manager.start()

        else:  # pragma: no cover
            msg = "TimeLimit cannot kill threads on your current platform (%r)."
            warnings.warn(msg % current_platform, category=RuntimeWarning, stacklevel=2)

    def before_process_message(self, broker, message):
        actor = broker.get_actor(message.actor_name)
        limit = message.options.get("time_limit") or actor.options.get("time_limit", self.time_limit)
        self.manager.add_timeout(threading.get_ident(), limit)

    def after_process_message(self, broker, message, *, result=None, exception=None):
        self.manager.remove_timeout(threading.get_ident())

    after_skip_message = after_process_message


class _CtypesTimeoutManager(Thread):
    def __init__(self, interval, logger=None):
        super().__init__(daemon=True)
        self.deadlines = {}
        self.interval = interval / 1000
        self.logger = logger or get_logger(__name__, type(self))
        self.mu = threading.RLock()

    def _handle_deadlines(self):
        current_time = monotonic()
        threads_to_kill = []
        with self.mu:
            for thread_id, deadline in self.deadlines.items():
                if deadline and current_time >= deadline:
                    self.logger.warning(
                        "Time limit exceeded. Raising exception in worker thread %r.",
                        thread_id,
                    )
                    self.deadlines[thread_id] = None
                    threads_to_kill.append(thread_id)

        for thread_id in threads_to_kill:
            raise_thread_exception(thread_id, TimeLimitExceeded)

    def run(self):
        while True:
            try:
                self._handle_deadlines()
            except Exception:  # pragma: no cover
                self.logger.exception("Unhandled error while running the time limit handler.")

            sleep(self.interval)

    def add_timeout(self, thread_id, ttl):
        with self.mu:
            self.deadlines[thread_id] = monotonic() + ttl / 1000

    def remove_timeout(self, thread_id):
        with self.mu:
            self.deadlines[thread_id] = None


class _GeventTimeoutManager:
    def __init__(self, logger=None):
        self.timers = {}
        self.logger = logger or get_logger(__name__, type(self))

    def start(self):
        pass

    def add_timeout(self, thread_id, ttl):
        self.timers[thread_id] = _GeventTimeout(
            logger=self.logger,
            thread_id=thread_id,
            after_expiration=lambda: self.timers.pop(thread_id, None),
            seconds=None if ttl == float("inf") else ttl / 1000,
            exception=TimeLimitExceeded,
        )
        self.timers[thread_id].start()

    def remove_timeout(self, thread_id):
        timer = self.timers.pop(thread_id, None)
        if timer is not None:
            timer.close()


_GeventTimeout: Optional[gevent.Timeout] = None
if is_gevent_active():
    from gevent import Timeout

    class __GeventTimeout(Timeout):
        """Cooperative timeout class for gevent with logging on timeouts."""

        def __init__(self, *args, logger=None, thread_id=None, after_expiration=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.logger = logger or get_logger(__name__, type(self))
            self.thread_id = thread_id
            self.after_expiration = after_expiration

        def _on_expiration(self, prev_greenlet, ex):
            self.logger.warning(
                "Time limit exceeded. Raising exception in worker thread %r.",
                self.thread_id,
            )
            res = super()._on_expiration(prev_greenlet, ex)
            if self.after_expiration is not None:
                self.after_expiration()
            return res

    _GeventTimeout = __GeventTimeout
