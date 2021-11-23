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

from pylibmc import Client, ClientPool

from ..backend import Missing, ResultBackend


class MemcachedBackend(ResultBackend):
    """A result backend for Memcached_.  This backend uses long
    polling to retrieve results.

    Parameters:
      namespace(str): A string with which to prefix result keys.
      encoder(Encoder): The encoder to use when storing and retrieving
        result data.  Defaults to :class:`.JSONEncoder`.
      pool(ClientPool): An optional pylibmc client pool to use.  If
        this is passed, all other connection params are ignored.
      pool_size(int): The size of the connection pool to use.
      **parameters: Connection parameters are passed directly
        to :class:`pylibmc.Client`.

    .. _memcached: https://memcached.org
    """

    def __init__(self, *, namespace="dramatiq-results", encoder=None, pool=None, pool_size=8, **parameters):
        super().__init__(namespace=namespace, encoder=encoder)
        self.pool = pool or ClientPool(Client(**parameters), pool_size)

    def _get(self, message_key):
        with self.pool.reserve(block=True) as client:
            data = client.get(message_key)
            if data is not None:
                return self.encoder.decode(data)
            return Missing

    def _store(self, message_key, result, ttl):
        result_data = self.encoder.encode(result)
        with self.pool.reserve(block=True) as client:
            client.set(message_key, result_data, time=int(ttl / 1000))
