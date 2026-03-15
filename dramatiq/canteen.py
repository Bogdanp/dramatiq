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

# Don't depend on *anything* in this module.  The contents of this
# module can and *will* change without notice.
import time
from contextlib import contextmanager
from ctypes import Array, Structure, c_bool, c_byte, c_int


class Buffer(Array):
    _length_ = 1024 * 1024
    _type_ = c_byte


# Canteen is the collective noun for a set of cutlery.
# It's OK to be cute every once in a while.
class Canteen(Structure):
    _fields_ = [
        ("initialized", c_bool),
        ("last_position", c_int),
        ("paths", Buffer),
    ]


def canteen_add(canteen, path):
    lo = canteen.last_position
    hi = canteen.last_position + len(path) + 1
    if hi > len(canteen.paths):
        raise RuntimeError("canteen is full")

    canteen.paths[lo:hi] = path.encode("utf-8") + b";"
    canteen.last_position = hi


def canteen_get(canteen, timeout=1):
    if not wait(canteen, timeout):
        return []

    data = bytes(canteen.paths[: canteen.last_position])
    return data.decode("utf-8").split(";")[:-1]


@contextmanager
def canteen_try_init(cv):
    if cv.initialized:
        yield False
        return

    with cv.get_lock():
        if cv.initialized:
            yield False
            return

        yield True
        cv.initialized = True


def wait(canteen, timeout):
    deadline = time.monotonic() + timeout
    while not canteen.initialized:
        if time.monotonic() > deadline:
            return False

        time.sleep(0)

    return True
