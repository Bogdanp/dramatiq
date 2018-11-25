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


class Barrier:
    """A distributed barrier.

    Examples:

      >>> from dramatiq.rate_limits import Barrier
      >>> from dramatiq.rate_limits.backends import RedisBackend

      >>> backend = RedisBackend()
      >>> barrier = Barrier(backend, "some-barrier", ttl=30_000)

      >>> created = barrier.create(parties=3)
      >>> barrier.wait(block=False)
      False
      >>> barrier.wait(block=False)
      False
      >>> barrier.wait(block=False)
      True

    Parameters:
      backend(BarrierBackend): The barrier backend to use.
      key(str): The key for the barrier.
      ttl(int): The TTL for the barrier key, in milliseconds.
    """

    def __init__(self, backend, key, *, ttl=900000):
        self.backend = backend
        self.key = key
        self.key_events = key + "@events"
        self.ttl = ttl

    def create(self, parties):
        """Create the barrier for the given number of parties.

        Parameters:
          parties(int): The number of parties to wait for.

        Returns:
          bool: Whether or not the new barrier was successfully created.
        """
        assert parties > 0, "parties must be a positive integer."
        return self.backend.add(self.key, parties, self.ttl)

    def wait(self, *, block=True, timeout=None):
        """Signal that a party has reached the barrier.

        Warning:
          Barrier blocking is currently only supported by the stub and
          Redis backends.

        Warning:
          Re-using keys between blocking calls may lead to undefined
          behaviour.  Make sure your barrier keys are always unique
          (use a UUID).

        Parameters:
          block(bool): Whether or not to block while waiting for the
            other parties.
          timeout(int): The maximum number of milliseconds to wait for
            the barrier to be cleared.

        Returns:
          bool: Whether or not the barrier has been reached by all parties.
        """
        cleared = not self.backend.decr(self.key, 1, 1, self.ttl)
        if cleared:
            self.backend.wait_notify(self.key_events, self.ttl)
            return True

        if block:
            return self.backend.wait(self.key_events, timeout)

        return False
