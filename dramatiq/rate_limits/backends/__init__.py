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

import warnings

from .stub import StubBackend

try:
    from .memcached import MemcachedBackend
except ImportError:  # pragma: no cover
    warnings.warn(
        "MemcachedBackend is not available.  Run `pip install dramatiq[memcached]` to add support for that backend.",
        category=ImportWarning,
        stacklevel=2,
    )

try:
    from .redis import RedisBackend
except ImportError:  # pragma: no cover
    warnings.warn(
        "RedisBackend is not available.  Run `pip install dramatiq[redis]` to add support for that backend.",
        category=ImportWarning,
        stacklevel=2,
    )


__all__ = ["StubBackend", "MemcachedBackend", "RedisBackend"]
