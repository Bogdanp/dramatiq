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

__all__ = ["StubBackend", "MemcachedBackend", "RedisBackend"]


def __getattr__(name):
    module_importer = _module_importers.get(name)
    if module_importer is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    return module_importer()


def import_memcached():
    try:
        from .memcached import MemcachedBackend

        return MemcachedBackend
    except ModuleNotFoundError:
        warnings.warn(
            "MemcachedBackend is not available.  Run `pip install dramatiq[memcached]` "
            "to add support for that backend.",
            category=ImportWarning,
            stacklevel=2,
        )
        raise


def import_redis():
    try:
        from .redis import RedisBackend

        return RedisBackend
    except ModuleNotFoundError:
        warnings.warn(
            "RedisBackend is not available.  Run `pip install dramatiq[redis]` to add support for that backend.",
            category=ImportWarning,
            stacklevel=2,
        )
        raise


_module_importers = {
    "MemcachedBackend": import_memcached,
    "RedisBackend": import_redis,
}
