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

from typing import Optional

from ..common import current_millis
from ..logging import get_logger
from .middleware import Middleware, SkipMessage


class AgeLimit(Middleware):
    """Middleware that drops messages that have been in the queue for
    too long.

    Parameters:
      max_age(int): The default message age limit in milliseconds.
        Defaults to ``None``, meaning that messages can exist
        indefinitely.
    """

    def __init__(self, *, max_age: Optional[int] = None) -> None:
        self.logger = get_logger(__name__, type(self))
        self.max_age = max_age

    @property
    def actor_options(self):
        return {"max_age"}

    def before_process_message(self, broker, message):
        actor = broker.get_actor(message.actor_name)
        max_age = message.options.get("max_age") or actor.options.get("max_age", self.max_age)
        if not max_age:
            return

        if current_millis() - message.message_timestamp >= max_age:
            self.logger.warning("Message %r has exceeded its age limit.", message.message_id)
            message.fail()
            raise SkipMessage("Message age limit exceeded")
