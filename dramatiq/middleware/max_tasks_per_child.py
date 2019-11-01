import threading

from .middleware import Middleware, RestartWorker
from ..logging import get_logger

# Tasks counter is per worker process
_tasks_counter = 0
_tasks_counter_lock = threading.Lock()


class MaxTasksPerChild(Middleware):
    """Middleware that lets you configure the maximum number of tasks a worker can execute
    before it’s replaced by a new process (like in celery)

    Parameters:
      max_tasks_per_child(int): Maximum number of tasks a worker process can process before it’s replaced with a new one. Default is no limit.
    """

    def __init__(self, *, max_tasks_per_child=None):
        self.logger = get_logger(__name__, type(self))
        self.max_tasks_per_child = max_tasks_per_child

    def after_process_message(self, broker, message, *, result=None, exception=None):
        global _tasks_counter
        self.logger.debug("Processing message, current tasks per child %r.", _tasks_counter)
        if self.max_tasks_per_child:
            with _tasks_counter_lock:
                _tasks_counter += 1
                if _tasks_counter >= self.max_tasks_per_child:
                    self.logger.debug("Max tasks per child counter limit reached (%r), restarting worker process.", _tasks_counter)
                    raise RestartWorker
