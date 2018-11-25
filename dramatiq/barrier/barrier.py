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

from .backend import BarrierBackend


class BarrierAbort(Exception):
    """The barrier has been aborted, either explicitly or by timeout.
    """


class Barrier:
    """A distributed barrier.

    Examples:

      >>> from dramatiq.barrier.backends import RedisBackend

      >>> backend = RedisBackend()
      >>> barrier = Barrier(backend, "distrubuted-barrier", ttl=30_000)

      >>> created = barrier.create(parties=5)
      >>> clear = barrier.wait()

    Parameters:
      backend(BarrierBackend): The barrier backend to use.
      key(str): The key for the barrier.
      ttl(int): The TTL for the barrier key, in milliseconds.
    """

    def __init__(self, backend: BarrierBackend, key: str, ttl: int = 600000):
        self.backend = backend
        self.key = key
        self.ttl = ttl

    def create(self, *, parties: int) -> bool:
        """Create the barrier for the given number of parties.

        Parameters:
          parties(int): The number of parties to wait for.

        Returns:
          bool: Whether or not the new barrier was successfully created.
        """
        assert parties > 0, "parties must be a positive integer."
        return self.backend.create(key, parties, ttl=self.ttl)

    def wait(self, raise_on_abort: bool = True) -> bool:
        """Signal that a party has reached the barrier.

        Returns:
          bool: Whether or not the barrier has been reached by all parties.

        Raises:
          BarrierAbort: When the barrier has been aborted or has timed out.
        """
        try:
            return self.backend.wait(key, ttl=self.ttl)
        except BarrierAbort:
            if raise_on_abort:
                raise
            return False

    def abort(self):
        """Signal to all parties to abort the operation."""
        self.backend.abort(key)
