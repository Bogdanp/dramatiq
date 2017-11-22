import json

from pylibmc import Client, ClientPool

from ..backend import ResultBackend, Missing


class MemcachedBackend(ResultBackend):
    """A result backend for Memcached_.

    Parameters:
      namespace(str): A string with which to prefix result keys.
      pool(ClientPool): An optional pylibmc client pool to use.  If
        this is passed, all other connection params are ignored.
      pool_size(int): The size of the connection pool to use.
      \**parameters(dict): Connection parameters are passed directly
        to :class:`pylibmc.Client`.

    .. _memcached: https://memcached.org
    """

    def __init__(self, *, namespace="dramatiq-results", pool=None, pool_size=8, **parameters):
        self.namespace = namespace
        self.pool = pool or ClientPool(Client(**parameters), pool_size)

    def _get(self, message_key):
        with self.pool.reserve(block=True) as client:
            data = client.get(message_key)
            if data is not None:
                return json.loads(data.decode("utf-8"))
            return Missing

    def _store(self, message_key, result, ttl):
        result_data = json.dumps(result, separators=(",", ":")).encode("utf-8")
        with self.pool.reserve(block=True) as client:
            client.set(message_key, result_data, time=int(ttl / 1000))
