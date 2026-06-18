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

import os
import warnings

from ..rate_limits import Barrier, RateLimiterBackend
from .middleware import Middleware


class GroupCallbacks(Middleware):
    """Middleware that enables adding completion callbacks to |Groups|.

    By default, completion callbacks are only fired when *all* tasks in
    a group succeed.  Set ``fire_on_failure=True`` to also fire them when
    the group finishes due to one or more tasks failing permanently
    (i.e. after all retries are exhausted or the message is skipped).

    Note: ``fire_on_failure`` requires the |Retries| middleware to be
    active (so that ``message.failed`` is set on permanent failures) and
    this middleware to run *after* it in the afte
    r-phase.  Because the
    after-phase runs middleware in reverse order, that means adding it
    *before* |Retries| in the middleware list, e.g.::

        broker.add_middleware(
            GroupCallbacks(backend, fire_on_failure=True),
            before=Retries,
        )

    Parameters:
      rate_limiter_backend(RateLimiterBackend): The rate limiter backend
        to use when creating group barriers.
      barrier_ttl(int): The TTL, in milliseconds, for group barriers.
        Defaults to 24 hours.
      fire_on_failure(bool): Whether to fire completion callbacks even
        when one or more tasks in the group have failed permanently.
        Defaults to False to preserve backwards-compatible behaviour.
    """

    def __init__(
        self,
        rate_limiter_backend: RateLimiterBackend,
        *,
        barrier_ttl: int = 86400 * 1000,
        fire_on_failure: bool = False,
    ) -> None:
        self.rate_limiter_backend = rate_limiter_backend
        self.fire_on_failure = fire_on_failure

        _barrier_ttl_env = os.getenv("dramatiq_group_callback_barrier_ttl", None)
        if _barrier_ttl_env is not None:
            warnings.warn(
                "Configuring the barrier TTL via the 'dramatiq_group_callback_barrier_ttl' environment variable is deprecated; "
                "use the `barrier_ttl` argument of the `GroupCallbacks` middleware instead. "
                "The 'dramatiq_group_callback_barrier_ttl' environment variable will be removed in dramatiq v3.0.0.",
                FutureWarning,
                stacklevel=2,
            )
            self.barrier_ttl = int(_barrier_ttl_env)
        else:
            self.barrier_ttl = barrier_ttl

    def _try_fire_callbacks(self, broker, message):
        from ..message import Message

        group_completion_uuid = message.options.get("group_completion_uuid")
        group_completion_callbacks = message.options.get("group_completion_callbacks")
        if group_completion_uuid and group_completion_callbacks:
            barrier = Barrier(
                self.rate_limiter_backend,
                group_completion_uuid,
                ttl=self.barrier_ttl,
            )
            if barrier.wait(block=False):
                for callback_message in group_completion_callbacks:
                    broker.enqueue(Message(**callback_message))

    def after_process_message(self, broker, message, *, result=None, exception=None):
        if exception is None:
            # Task succeeded -- always fire.
            self._try_fire_callbacks(broker, message)
        elif self.fire_on_failure and message.failed:
            # Task failed permanently (retries exhausted) and the caller
            # opted into failure callbacks -- fire.
            self._try_fire_callbacks(broker, message)

    def after_skip_message(self, broker, message):
        if self.fire_on_failure:
            # Skipped messages (e.g. AgeLimit) count as permanent
            # failures when fire_on_failure is enabled.
            self._try_fire_callbacks(broker, message)
