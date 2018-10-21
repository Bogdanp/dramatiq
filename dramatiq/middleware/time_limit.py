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

import threading
import warnings
from threading import Thread
from time import monotonic, sleep

from ..logging import get_logger
from .middleware import Middleware
from .threading import Interrupt, current_platform, raise_thread_exception, supported_platforms


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
      time_limit(int): The maximum number of milliseconds actors may
        run for.
      interval(int): The interval (in milliseconds) with which to
        check for actors that have exceeded the limit.
    """

    def __init__(self, *, time_limit=600000, interval=1000):
        self.logger = get_logger(__name__, type(self))
        self.time_limit = time_limit
        self.interval = interval / 1000
        self.deadlines = {}

    def _handle(self):
        current_time = monotonic()
        for thread_id, deadline in self.deadlines.items():
            if deadline and current_time >= deadline:
                self.logger.warning("Time limit exceeded. Raising exception in worker thread %r.", thread_id)
                self.deadlines[thread_id] = None
                raise_thread_exception(thread_id, TimeLimitExceeded)

    def _timer(self):
        while True:
            try:
                self._handle()
            except Exception:  # pragma: no cover
                self.logger.exception("Unhandled error while running the time limit handler.")

            sleep(self.interval)

    @property
    def actor_options(self):
        return {"time_limit"}

    def after_process_boot(self, broker):
        if current_platform in supported_platforms:
            thread = Thread(target=self._timer, daemon=True)
            thread.start()

        else:  # pragma: no cover
            msg = "TimeLimit cannot kill threads on your current platform (%r)."
            warnings.warn(msg % current_platform, category=RuntimeWarning, stacklevel=2)

    def before_process_message(self, broker, message):
        actor = broker.get_actor(message.actor_name)
        limit = message.options.get("time_limit") or actor.options.get("time_limit", self.time_limit)
        deadline = monotonic() + limit / 1000
        self.deadlines[threading.get_ident()] = deadline

    def after_process_message(self, broker, message, *, result=None, exception=None):
        self.deadlines[threading.get_ident()] = None

    after_skip_message = after_process_message
