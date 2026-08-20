# This file is a part of Dramatiq.
#
# Copyright (C) 2026 CLEARTYPE SRL <bogdan@cleartype.io>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pickle
import threading
import time

from dramatiq.compat import StreamablePipe


class SlowPipe:
    def __init__(self):
        self.active_writes = 0
        self.concurrent_writes = False
        self.lock = threading.Lock()

    def send_bytes(self, data):
        with self.lock:
            self.active_writes += 1
            self.concurrent_writes |= self.active_writes > 1

        time.sleep(0.01)

        with self.lock:
            self.active_writes -= 1


class PickleablePipe:
    pass


def test_streamable_pipe_serializes_writes():
    pipe = SlowPipe()
    stream = StreamablePipe(pipe)
    start = threading.Barrier(2)

    def write():
        start.wait()
        stream.write("message")

    writers = [threading.Thread(target=write) for _ in range(2)]
    for writer in writers:
        writer.start()
    for writer in writers:
        writer.join()

    assert not pipe.concurrent_writes


def test_streamable_pipe_can_be_pickled():
    stream = StreamablePipe(PickleablePipe())
    restored = pickle.loads(pickle.dumps(stream))

    assert restored.encoding == "utf-8"
    assert isinstance(restored.pipe, PickleablePipe)
