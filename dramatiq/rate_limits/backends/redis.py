import redis

from ..backend import RateLimiterBackend


class RedisBackend(RateLimiterBackend):
    """A rate limiter backend for Redis_.

    Parameters:
      \**parameters(dict): Connection parameters are passed directly
        to :class:`redis.StrictRedis`.

    .. _redis: https://redis.io
    """

    def __init__(self, **parameters):
        self.client = redis.StrictRedis(**parameters)

    def add(self, key, value, ttl):
        return bool(self.client.set(key, value, px=ttl, nx=True))

    def incr(self, key, amount, maximum, ttl):
        with self.client.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(key)
                    value = int(pipe.get(key) or b"0")
                    value += amount
                    if value > maximum:
                        return False

                    pipe.multi()
                    pipe.set(key, value, px=ttl)
                    pipe.execute()
                    return True
                except redis.WatchError:
                    continue

    def decr(self, key, amount, minimum, ttl):
        with self.client.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(key)
                    value = int(pipe.get(key) or b"0")
                    value -= amount
                    if value < minimum:
                        return False

                    pipe.multi()
                    pipe.set(key, value, px=ttl)
                    pipe.execute()
                    return True
                except redis.WatchError:
                    continue

    def incr_and_sum(self, key, keys, amount, maximum, ttl):
        with self.client.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(key, *keys)
                    value = int(pipe.get(key) or b"0")
                    value += amount
                    if value > maximum:
                        return False

                    values = pipe.mget(keys)
                    total = amount + sum(int(n) for n in values if n)
                    if total > maximum:
                        return False

                    pipe.multi()
                    pipe.set(key, value, px=ttl)
                    pipe.execute()
                    return True
                except redis.WatchError:
                    continue
