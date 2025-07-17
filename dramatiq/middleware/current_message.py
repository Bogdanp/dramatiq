# This file is a part of Dramatiq.
#
# Copyright (C) 2019 CLEARTYPE SRL <bogdan@cleartype.io>
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

import contextvars
from typing import TYPE_CHECKING, Any, Optional

from .middleware import Middleware

if TYPE_CHECKING:
    from ..message import Message


class CurrentMessage(Middleware):
    """Middleware that exposes the current message via a thread-local
    variable.

    Example:
      >>> import dramatiq
      >>> from dramatiq.middleware import CurrentMessage

      >>> @dramatiq.actor
      ... def example(x):
      ...     print(CurrentMessage.get_current_message())
      ...
      >>> example.send(1)

    """

    _MESSAGE: contextvars.ContextVar[Optional[Message[Any]]] = contextvars.ContextVar("_MESSAGE", default=None)

    @classmethod
    def get_current_message(cls) -> Optional[Message[Any]]:
        """Get the message that triggered the current actor.  Messages
        are thread local so this returns ``None`` when called outside
        of actor code.
        """
        return cls._MESSAGE.get()

    def before_process_message(self, broker, message):
        self._MESSAGE.set(message)

    def after_process_message(self, broker, message, *, result=None, exception=None):
        self._MESSAGE.set(None)
