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

import ctypes
import inspect
import platform

from .logging import get_logger

__all__ = [
    "Interrupt",
    "current_platform",
    "is_gevent_active",
    "raise_thread_exception",
    "supported_platforms",
]


logger = get_logger(__name__)

current_platform = platform.python_implementation()
python_version = platform.python_version_tuple()
thread_id_ctype = ctypes.c_long if python_version < ("3", "7") else ctypes.c_ulong
supported_platforms = {"CPython"}


def is_gevent_active():
    """Detect if gevent monkey patching is active."""
    try:
        from gevent import monkey
    except ImportError:  # pragma: no cover
        return False
    return bool(monkey.saved)


class Interrupt(BaseException):
    """Base class for exceptions used to asynchronously interrupt a
    thread's execution.  An actor may catch these exceptions in order
    to respond gracefully, such as performing any necessary cleanup.

    This is *not* a subclass of ``DramatiqError`` to avoid it being
    caught unintentionally.
    """


def raise_thread_exception(thread_id, exception):
    """Raise an exception in a thread.

    Currently, this is only available on CPython.

    Note:
      This works by setting an async exception in the thread.  This means
      that the exception will only get called the next time that thread
      acquires the GIL.  Concretely, this means that this middleware can't
      cancel system calls.
    """
    if current_platform == "CPython":
        _raise_thread_exception_cpython(thread_id, exception)
    else:
        message = "Setting thread exceptions (%s) is not supported for your current platform (%r)."
        exctype = (exception if inspect.isclass(exception) else type(exception)).__name__
        logger.critical(message, exctype, current_platform)


def _raise_thread_exception_cpython(thread_id, exception):
    exctype = (exception if inspect.isclass(exception) else type(exception)).__name__
    thread_id = thread_id_ctype(thread_id)
    exception = ctypes.py_object(exception)
    count = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, exception)
    if count == 0:
        logger.critical("Failed to set exception (%s) in thread %r.", exctype, thread_id.value)
    elif count > 1:  # pragma: no cover
        logger.critical("Exception (%s) was set in multiple threads.  Undoing...", exctype)
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, ctypes.c_long(0))
