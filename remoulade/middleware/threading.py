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

import ctypes
import inspect
import platform

from ..logging import get_logger

__all__ = ["Interrupt", "raise_thread_exception"]


logger = get_logger(__name__)

current_platform = platform.python_implementation()
supported_platforms = {"CPython"}


class Interrupt(BaseException):
    """Base class for exceptions used to asynchronously interrupt a
    thread's execution.  An actor may catch these exceptions in order
    to respond gracefully, such as performing any necessary cleanup.

    This is *not* a subclass of ``RemouladeError`` to avoid it being
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
    thread_id = ctypes.c_long(thread_id)
    exception = ctypes.py_object(exception)
    count = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, exception)
    if count == 0:
        logger.critical("Failed to set exception (%s) in thread %r.", exctype, thread_id.value)
    elif count > 1:  # pragma: no cover
        logger.critical("Exception (%s) was set in multiple threads.  Undoing...", exctype)
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, ctypes.c_long(0))
