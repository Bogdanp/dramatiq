import threading

class TaskRegistry:
    """
    Registry for mapping task identifiers to their respective handlers.
    Implements a thread-safe check-and-set pattern to prevent handler overwrites.
    """
    def __init__(self):
        self._tasks = {}
        self._lock = threading.Lock()

    def register(self, name, actor):
        with self._lock:
            if name in self._tasks:
                raise KeyError(f"Task {name} is already registered")
            self._tasks[name] = actor

    def lookup(self, name):
        with self._lock:
            return self._tasks.get(name)

    def __contains__(self, name):
        with self._lock:
            return name in self._tasks
