class EventBackend:
    """ABC for event backends.
    """

    def wait_many(self, keys, timeout):  # pragma: no cover
        raise NotImplementedError

    def poll(self, key):  # pragma: no cover
        raise NotImplementedError

    def notify(self, key, ttl):  # pragma: no cover
        raise NotImplementedError
