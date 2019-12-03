import redis

from ..backend import EventBackend


class RedisBackend(EventBackend):
    """A rate limiter backend for Redis_.

    Parameters:
      client(Redis): An optional client.  If this is passed,
        then all other parameters are ignored.
      url(str): An optional connection URL.  If both a URL and
        connection paramters are provided, the URL is used.
      **parameters(dict): Connection parameters are passed directly
        to :class:`redis.Redis`.

    .. _redis: https://redis.io
    """

    def __init__(self, *, client=None, url=None, **parameters):
        if url is not None:
            parameters["connection_pool"] = redis.ConnectionPool.from_url(url)

        # TODO: Replace usages of StrictRedis (redis-py 2.x) with Redis in Dramatiq 2.0.
        self.client = client or redis.StrictRedis(**parameters)

    def wait_many(self, keys, timeout):
        assert timeout is None or timeout >= 1000, "wait timeouts must be >= 1000"
        event = self.client.blpop(keys, (timeout or 0) // 1000)
        if event is None:
            return None
        key, value = event
        if value != b"x":
            return None
        return key

    def poll(self, key):
        event = self.client.lpop(key)
        return event == b"x"

    def notify(self, key, ttl):
        with self.client.pipeline() as pipe:
            pipe.rpush(key, b"x")
            pipe.pexpire(key, ttl)
            pipe.execute()
