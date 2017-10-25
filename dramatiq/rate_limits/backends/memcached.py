from pylibmc import Client, ClientPool, NotFound

from ..backend import RateLimiterBackend


class MemcachedBackend(RateLimiterBackend):
    """A rate limiter backend for Memcached_.

    Examples:

      >>> from dramatiq.rate_limits.backends import MemcachedBackend
      >>> backend = MemcachedBackend(servers=["127.0.0.1"], binary=True)

    Parameters:
      pool_size(int): The size of the connection pool to use.
      \**parameters(dict): Connection parameters are passed directly
        to :class:`pylibmc.Client`.

    .. _memcached: https://memcached.org
    """

    def __init__(self, *, pool_size=8, **parameters):
        behaviors = parameters.setdefault("behaviors", {})
        behaviors["cas"] = True

        self.client = client = Client(**parameters)
        self.pool = ClientPool(client, pool_size)

    def add(self, key, value, ttl):
        with self.pool.reserve(block=True) as client:
            return client.add(key, value, time=int(ttl / 1000))

    def incr(self, key, amount, maximum, ttl):
        ttl = int(ttl / 1000)
        with self.pool.reserve(block=True) as client:
            while True:
                value, cid = client.gets(key)
                if cid is None:
                    return False

                value += amount
                if value > maximum:
                    return False

                try:
                    swapped = client.cas(key, value, cid, ttl)
                    if swapped:
                        return True
                except NotFound:  # pragma: no cover
                    continue

    def decr(self, key, amount, minimum, ttl):
        ttl = int(ttl / 1000)
        with self.pool.reserve(block=True) as client:
            while True:
                value, cid = client.gets(key)
                if cid is None:
                    return False

                value -= amount
                if value < minimum:
                    return False

                try:
                    swapped = client.cas(key, value, cid, ttl)
                    if swapped:
                        return True
                except NotFound:  # pragma: no cover
                    continue

    def incr_and_sum(self, key, keys, amount, maximum, ttl):
        ttl = int(ttl / 1000)
        with self.pool.reserve(block=True) as client:
            client.add(key, 0, time=ttl)

            while True:
                value, cid = client.gets(key)
                if cid is None:
                    return False

                value += amount
                if value > maximum:
                    return False

                mapping = client.get_multi(keys)
                total = amount + sum(mapping.values())
                if total > maximum:
                    return False

                try:
                    swapped = client.cas(key, value, cid, ttl)
                    if swapped:
                        return True
                except NotFound:  # pragma: no cover
                    continue
