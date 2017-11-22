import json
import time

from ..backend import ResultBackend, Missing


class StubBackend(ResultBackend):
    """An in-memory result backend.  For use in unit tests.
    """

    def __init__(self, *, namespace="dramatiq"):
        self.namespace = namespace
        self.results = {}

    def _get(self, message_key):
        data, expiration = self.results.get(message_key, (None, None))
        if data is not None and time.monotonic() < expiration:
            return json.loads(data.decode("utf-8"))
        return Missing

    def _store(self, message_key, result, ttl):
        result_data = json.dumps(result, separators=(",", ":")).encode("utf-8")
        expiration = time.monotonic() + int(ttl / 1000)
        self.results[message_key] = (result_data, expiration)
