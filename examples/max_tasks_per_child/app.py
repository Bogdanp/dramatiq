import os
import signal
from threading import Lock

import dramatiq
from dramatiq import Middleware, get_logger


class MaxTasksPerChild(Middleware):
    def __init__(self, max_tasks=100):
        self.counter_mu = Lock()
        self.counter = max_tasks
        self.signaled = False
        self.logger = get_logger("max_tasks_per_child.app", MaxTasksPerChild)

    def after_process_message(self, broker, message, *, result=None, exception=None):
        with self.counter_mu:
            self.counter -= 1
            self.logger.debug("Remaining tasks: %d.", self.counter)
            if self.counter <= 0 and not self.signaled:
                self.logger.warning("Counter reached zero. Signaling current process.")
                os.kill(os.getppid(), getattr(signal, "SIGHUP", signal.SIGTERM))
                self.signaled = True


broker = dramatiq.get_broker()
broker.add_middleware(MaxTasksPerChild())


@dramatiq.actor
def example():
    pass


if __name__ == "__main__":
    for _ in range(105):
        example.send()
