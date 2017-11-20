import json
import redis

from ..backend import ResultBackend, Missing


class RedisBackend(ResultBackend):
    """A result backend for Redis_.

    Parameters:
      namespace(str): A string with which to prefix result keys.
      client(StrictRedis): An optional client.  If this is passed,
        then all other parameters are ignored.
      \**parameters(dict): Connection parameters are passed directly
        to :class:`redis.StrictRedis`.

    .. _redis: https://redis.io
    """

    def __init__(self, *, namespace="dramatiq-results", client=None, **parameters):
        self.namespace = namespace
        self.client = client or redis.StrictRedis(**parameters)

    def _get(self, message_key):
        data = self.client.get(message_key)
        if data is not None:
            return json.loads(data.decode("utf-8"))
        return Missing

    def _store(self, message_key, result, ttl):
        result_data = json.dumps(result, separators=(",", ":")).encode("utf-8")
        expiration = int(ttl / 1000)
        self.client.setex(message_key, expiration, result_data)
