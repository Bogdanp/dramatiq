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

import os

from ..rate_limits import Barrier
from .middleware import Middleware

GROUP_CALLBACK_BARRIER_TTL = int(os.getenv("dramatiq_group_callback_barrier_ttl", "86400000"))


class GroupCallbacks(Middleware):
    def __init__(self, rate_limiter_backend):
        self.rate_limiter_backend = rate_limiter_backend

    def after_process_message(self, broker, message, *, result=None, exception=None):
        from ..message import Message

        if exception is None:
            group_completion_uuid = message.options.get("group_completion_uuid")
            group_completion_callbacks = message.options.get("group_completion_callbacks")
            if group_completion_uuid and group_completion_callbacks:
                barrier = Barrier(self.rate_limiter_backend, group_completion_uuid, ttl=GROUP_CALLBACK_BARRIER_TTL)
                if barrier.wait(block=False):
                    for message in group_completion_callbacks:
                        broker.enqueue(Message(**message))
