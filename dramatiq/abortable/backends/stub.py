from threading import Condition

from ..backend import EventBackend


class StubBackend(EventBackend):
    """ABC for rate limiter backends.
    """
    def __init__(self):
        self.condition = Condition()
        self.events = set()

    def wait_many(self, keys, timeout):
        with self.condition:
            if self.condition.wait_for(lambda: self._anyset(keys), timeout=timeout / 1000):
                for key in keys:
                    if key in self.events:
                        self.events.remove(key)
                        return key

    def poll(self, key):
        with self.condition:
            if key in self.events:
                self.events.remove(key)
                return True
        return False

    def notify(self, key, ttl):
        with self.condition:
            self.events.add(key)
            self.condition.notify_all()

    def _anyset(self, keys):
        return any(k in self.events for k in keys)
