# This file is a part of Remoulade.
#
# Copyright (C) 2017,2018 CLEARTYPE SRL <bogdan@cleartype.io>
#
# Remoulade is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# Remoulade is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import platform

from .age_limit import AgeLimit
from .callbacks import Callbacks
from .middleware import Middleware, MiddlewareError, SkipMessage
from .pipelines import Pipelines
from .retries import Retries
from .shutdown import Shutdown, ShutdownNotifications
from .threading import Interrupt, raise_thread_exception
from .time_limit import TimeLimit, TimeLimitExceeded

CURRENT_OS = platform.system()

if CURRENT_OS != "Windows":
    from .prometheus import Prometheus  # noqa: F401


__all__ = [
    # Basics
    "Middleware", "MiddlewareError", "SkipMessage",

    # Threading
    "Interrupt", "raise_thread_exception",

    # Middlewares
    "AgeLimit", "Callbacks", "Pipelines", "Retries",
    "Shutdown", "ShutdownNotifications", "TimeLimit",
    "TimeLimitExceeded"
]

if CURRENT_OS != "Windows":
    __all__.append("Prometheus")


#: The list of middleware that are enabled by default.
default_middleware = [
    AgeLimit, TimeLimit, ShutdownNotifications,
    Callbacks, Pipelines, Retries
]
