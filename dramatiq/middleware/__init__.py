# This file is a part of Dramatiq.
#
# Copyright (C) 2017,2018,2019 CLEARTYPE SRL <bogdan@cleartype.io>
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

from .age_limit import AgeLimit
from .callbacks import Callbacks
from .current_message import CurrentMessage
from .group_callbacks import GroupCallbacks
from .middleware import Middleware, MiddlewareError, SkipMessage
from .pipelines import Pipelines
from .prometheus import Prometheus
from .retries import Retries
from .shutdown import Shutdown, ShutdownNotifications
from .threading import Interrupt, raise_thread_exception
from .time_limit import TimeLimit, TimeLimitExceeded

__all__ = [
    # Basics
    "Middleware", "MiddlewareError", "SkipMessage",

    # Threading
    "Interrupt", "raise_thread_exception",

    # Middlewares
    "AgeLimit", "Callbacks", "CurrentMessage", "GroupCallbacks", "Pipelines", "Retries",
    "Shutdown", "ShutdownNotifications", "TimeLimit", "TimeLimitExceeded",
    "Prometheus",
]


#: The list of middleware that are enabled by default.
default_middleware = [
    Prometheus, AgeLimit, TimeLimit, ShutdownNotifications, Callbacks, Pipelines, Retries
]
