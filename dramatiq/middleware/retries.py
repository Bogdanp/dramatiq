import traceback

from random import uniform

from ..common import current_millis
from ..logging import get_logger
from .middleware import Middleware


class Retries(Middleware):
    """Middleware that automatically retries failed tasks with
    exponential backoff.

    Parameters:
      max_age(int): The maximum task age in milliseconds.
      max_retires(int): The maximum number of times tasks can be retried.
      min_backoff(int): The minimum amount of backoff milliseconds to
        apply to retried tasks.  Defaults to 15 seconds.
      max_backoff(int): The maximum amount of backoff milliseconds to
        apply to retried tasks.  Defaults to 30 days.
    """

    def __init__(self, *, max_age=None, max_retries=None, min_backoff=15000, max_backoff=2592000000):
        self.logger = get_logger(__name__, type(self))
        self.max_age = max_age
        self.max_retries = max_retries
        self.min_backoff = min_backoff
        self.max_backoff = max_backoff

    @property
    def actor_options(self):
        return set([
            "max_age",
            "max_retries",
            "min_backoff",
            "max_backoff",
        ])

    def after_process_message(self, broker, message, *, result=None, exception=None):
        if exception is None:
            return

        actor = broker.get_actor(message.actor_name)
        max_age = actor.options.get("max_age", self.max_age)
        max_retries = actor.options.get("max_retries", self.max_retries)
        retries = message.options.setdefault("retries", 0)
        if max_retries is not None and retries >= max_retries:
            self.logger.warning("Retries exceeded for message %r.", message.message_id)
            message.fail()
            return

        if max_age is not None and current_millis() - message.message_timestamp >= max_age:
            self.logger.warning("Message %r has exceeded its age limit.", message.message_id)
            message.fail()
            return

        message.options["retries"] += 1
        message.options["traceback"] = traceback.format_exc(limit=30)
        min_backoff = actor.options.get("min_backoff", self.min_backoff)
        max_backoff = actor.options.get("max_backoff", self.max_backoff)
        delay = min(min_backoff * 2 ** retries, max_backoff) / 2
        delay = int(delay + uniform(0, delay))
        self.logger.info("Retrying message %r in %d milliseconds.", message.message_id, delay)
        broker.enqueue(message, delay=delay)
