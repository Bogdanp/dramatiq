import traceback

from ..common import compute_backoff
from ..logging import get_logger
from .middleware import Middleware


class Retries(Middleware):
    """Middleware that automatically retries failed tasks with
    exponential backoff.

    Parameters:
      max_retires(int): The maximum number of times tasks can be retried.
      min_backoff(int): The minimum amount of backoff milliseconds to
        apply to retried tasks.  Defaults to 15 seconds.
      max_backoff(int): The maximum amount of backoff milliseconds to
        apply to retried tasks.  Defaults to 30 days.
    """

    def __init__(self, *, max_retries=None, min_backoff=15000, max_backoff=2592000000):
        self.logger = get_logger(__name__, type(self))
        self.max_retries = max_retries
        self.min_backoff = min_backoff
        self.max_backoff = max_backoff

    @property
    def actor_options(self):
        return set([
            "max_retries",
            "min_backoff",
            "max_backoff",
        ])

    def after_process_message(self, broker, message, *, result=None, exception=None):
        if exception is None:
            return

        actor = broker.get_actor(message.actor_name)
        max_retries = actor.options.get("max_retries", self.max_retries)
        retries = message.options.setdefault("retries", 0)
        if max_retries is not None and retries >= max_retries:
            self.logger.warning("Retries exceeded for message %r.", message.message_id)
            message.fail()
            return

        previous_id = message.message_id
        message = message.new_id()
        message.options["retries"] += 1
        message.options["traceback"] = traceback.format_exc(limit=30)
        min_backoff = actor.options.get("min_backoff", self.min_backoff)
        max_backoff = actor.options.get("max_backoff", self.max_backoff)
        _, backoff = compute_backoff(retries, factor=min_backoff, max_backoff=max_backoff)
        self.logger.info("Retrying message %r as %r in %d milliseconds.", previous_id, message.message_id, backoff)
        broker.enqueue(message, delay=backoff)
