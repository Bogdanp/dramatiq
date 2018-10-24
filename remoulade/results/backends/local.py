from ..backend import ResultBackend
from ..errors import ResultError


class LocalBackend(ResultBackend):
    """An in-memory result backend. For use with LocalBroker only.

    We need to be careful here: if an actor store its results and never retrieves it, we may store all its results
    and never delete it. Resulting in a memory leak.
    """

    results = {}

    def _get(self, message_key):
        try:
            return self.results.pop(message_key)
        except KeyError:
            message = 'The result corresponding to the message %s was not saved (have you set store_result = True)'
            raise ResultError(message % message_key)

    def _store(self, message_key, result, _):
        self.results[message_key] = result
