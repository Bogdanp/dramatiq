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

# Don't depend on *anything* in this module.  The contents of this
# module can and *will* change without notice.


class StreamablePipe:
    """Wrap a multiprocessing.connection.PipeConnection so it can be
    used with logging's StreamHandler.

    Parameters:
      pipe(multiprocessing.connection.PipeConnection): writable end of
        the pipe to be used for transmitting child worker logging data
        to parent.
    """

    def __init__(self, pipe):
        self.pipe = pipe

    def flush(self):
        pass

    def close(self):
        self.pipe.close()

    def read(self):
        return self.pipe.recv()

    def write(self, s):
        self.pipe.send(s)
