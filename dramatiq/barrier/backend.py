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


class BarrierBackend:
    """ABC for barrier backends.
    """

    def create(self, key: str, parties: int, ttl: int):  # pragma: no cover
        """Create the barrier.

        Parameters:
          key(str): The key for the barrier.
          parties(int): The number of parties to wait for.
          ttl(int): The max amount of time in milliseconds the key can
            live in the backend for.
        """
        raise NotImplementedError

    def wait(self, key: str, ttl: int):  # pragma: no cover
        """Record that a party has reached the barrier.

        Parameters:
          key(str): The key for the barrier.
          ttl(int): The max amount of time in milliseconds the key can
            live in the backend for.

        Returns:
          bool: Whether or not the barrier has been reached by all parties.

        Raises:
          BarrierAbort: When the key doesn't exist in the backend.
        """
        raise NotImplementedError

    def abort(self, key: str):  # pragma: no cover
        """Explicity remove the key from the backend to abort the barrier.

        Parameters:
          key(str): The key for the barrier.

        Returns:
          bool: True if the key was successfully decremented.
        """
        raise NotImplementedError
