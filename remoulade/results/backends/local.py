from ..backend import ForgottenResult, Missing, ResultBackend


class LocalBackend(ResultBackend):
    """An in-memory result backend. For use with LocalBroker only.

    We need to be careful here: if an actor store its results and never forget it, we may store all its results
    and never delete it. Resulting in a memory leak.
    """

    results = {}
    forgotten_results = set()

    def _get(self, message_key, forget: bool = False):
        if message_key in self.forgotten_results:
            return ForgottenResult.asdict()

        try:
            if forget:
                data = self.results.pop(message_key)
                self.forgotten_results.add(message_key)
                return data
            else:
                return self.results[message_key]
        except KeyError:
            return Missing

    def _store(self, message_key, result, _):
        self.results[message_key] = result

    def increment_group_completion(self, group_id: str) -> int:
        group_completion_key = self.build_group_completion_key(group_id)
        completion = self.results.get(group_completion_key, 0) + 1
        self.results[group_completion_key] = completion
        return completion
