# This file is a part of Dramatiq.
#
# Copyright (C) 2023 CLEARTYPE SRL <bogdan@cleartype.io>
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

from ..asyncio import EventLoopThread, get_event_loop_thread, set_event_loop_thread
from ..logging import get_logger
from .middleware import Middleware


class AsyncIO(Middleware):
    """This middleware manages the event loop thread for async actors."""

    def __init__(self) -> None:
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
