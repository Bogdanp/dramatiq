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

# Don't depend on *anything* in this module.  The contents of this
# module can and *will* change without notice.
import sys
from contextlib import contextmanager


class StreamablePipe:
    """Wrap a multiprocessing.connection.Connection so it can be used
    with logging's StreamHandler.

    Parameters:
      pipe(multiprocessing.connection.Connection): writable end of the
        pipe to be used for transmitting child worker logging data to
        parent.
    """

    def __init__(self, pipe, *, encoding="utf-8"):
        self.encoding = encoding
        self.pipe = pipe

    def fileno(self):
        return self.pipe.fileno()

    def isatty(self):
        return False

    def flush(self):
        pass

    def close(self):
        self.pipe.close()

    def read(self):  # pragma: no cover
        raise NotImplementedError("StreamablePipes cannot be read from!")

    def write(self, s):
        self.pipe.send_bytes(s.encode(self.encoding, errors="replace"))

    @property
    def closed(self):
        return self.pipe.closed


def file_or_stderr(filename, *, mode="a", encoding="utf-8"):
    """Returns a context object wrapping either the given file or
    stderr (if filename is None).  This makes dealing with log files
    more convenient.
    """
    if filename is not None:
        return open(filename, mode, encoding=encoding)

    @contextmanager
    def stderr_wrapper():
        yield sys.stderr

    return stderr_wrapper()
