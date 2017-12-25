import time

from ..backend import ResultBackend, Missing


class StubBackend(ResultBackend):
    """An in-memory result backend.  For use in unit tests.

    Parameters:
      namespace(str): A string with which to prefix result keys.
      encoder(Encoder): The encoder to use when storing and retrieving
        result data.  Defaults to :class:`.JSONEncoder`.
    """

    results = {}

    def _get(self, message_key):
        data, expiration = self.results.get(message_key, (None, None))
        if data is not None and time.monotonic() < expiration:
            return self.encoder.decode(data)
        return Missing

    def _store(self, message_key, result, ttl):
        result_data = self.encoder.encode(result)
        expiration = time.monotonic() + int(ttl / 1000)
        self.results[message_key] = (result_data, expiration)
