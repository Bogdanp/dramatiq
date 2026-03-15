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

from ..logging import get_logger
from .middleware import Middleware
from .threading import (
    Interrupt,
    current_platform,
    is_gevent_active,
    raise_thread_exception,
    supported_platforms,
)


class Shutdown(Interrupt):
    """Exception used to interrupt worker threads when their worker
    processes have been signaled for termination.
    """


class ShutdownNotifications(Middleware):
    """Middleware that interrupts actors whose worker process has been
    signaled for termination.
    Currently, this is only available on CPython.

    Note:
      This works by setting an async exception in the worker thread
      that runs the actor.  This means that the exception will only get
      called the next time that thread acquires the GIL.  Concretely,
      this means that this middleware can't cancel system calls.

    Parameters:
      notify_shutdown(bool): When True, the actor will be interrupted
        if the worker process was terminated.
        Defaults to False, meaning actors will not be interrupted, and allowed to finish.
    """

    def __init__(self, notify_shutdown: bool = False) -> None:
        self.logger = get_logger(__name__, type(self))
        self.notify_shutdown = notify_shutdown

        self.manager: _ShutdownManager
        if is_gevent_active():
            self.manager = _GeventShutdownManager(self.logger)
        else:
            self.manager = _CtypesShutdownManager(self.logger)

    @property
    def actor_options(self):
        return {"notify_shutdown"}

    def should_notify(self, actor, message):
        notify = message.options.get("notify_shutdown")
        if notify is None:
            notify = actor.options.get("notify_shutdown")
        if notify is None:
            notify = self.notify_shutdown
        return bool(notify)

    def after_process_boot(self, broker):
        if current_platform not in supported_platforms:  # pragma: no cover
            msg = "ShutdownNotifications cannot kill threads on your current platform (%r)."
            warnings.warn(msg % current_platform, category=RuntimeWarning, stacklevel=2)

    def before_worker_shutdown(self, broker, worker):
        self.logger.debug("Sending shutdown notification to worker threads...")
        self.manager.shutdown()

    def before_process_message(self, broker, message):
        actor = broker.get_actor(message.actor_name)

        if self.should_notify(actor, message):
            self.manager.add_notification()

    def after_process_message(self, broker, message, *, result=None, exception=None):
        self.manager.remove_notification()

    after_skip_message = after_process_message


class _ShutdownManager:

    def __init__(self, logger=None) -> None:  # pragma: no cover
        raise NotImplementedError

    def add_notification(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def remove_notification(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def shutdown(self) -> None:  # pragma: no cover
        raise NotImplementedError


class _CtypesShutdownManager(_ShutdownManager):

    def __init__(self, logger=None):
        self.logger = logger or get_logger(__name__, type(self))
        self.notifications = set()

    def add_notification(self):
        self.notifications.add(threading.get_ident())

    def remove_notification(self):
        self.notifications.discard(threading.get_ident())

    def shutdown(self):
        for thread_id in self.notifications:
            self.logger.info(
                "Worker shutdown notification. Raising exception in worker thread %r.",
                thread_id,
            )
            raise_thread_exception(thread_id, Shutdown)


if is_gevent_active():
    from gevent import getcurrent

    class _GeventShutdownManager(_ShutdownManager):

        def __init__(self, logger=None):
            self.logger = logger or get_logger(__name__, type(self))
            self.notification_greenlets = set()

        def add_notification(self):
            current_greenlet = getcurrent()
            # Get and store the threading ident rather than using the greenlet's
            # minimal_ident for logging consistency with the time limit middleware.
            thread_id = threading.get_ident()
            self.notification_greenlets.add((thread_id, current_greenlet))

        def remove_notification(self):
            current_greenlet = getcurrent()
            thread_id = threading.get_ident()
            self.notification_greenlets.discard((thread_id, current_greenlet))

        def shutdown(self):
            for thread_id, greenlet in self.notification_greenlets:
                self.logger.info(
                    "Worker shutdown notification. Raising exception in worker thread %r.",
                    thread_id,
                )
                greenlet.kill(Shutdown, block=False)
