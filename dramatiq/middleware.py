import logging

from random import uniform
from time import time


class Middleware:
    """Base class for broker middleware.  The default implementations
    for all hooks are no-ops and subclasses may implement whatever
    subset of hooks they like.
    """

    @property
    def actor_options(self):
        """The set of options that may be set on each actor to
        configure interactions with this middleware.
        """
        return set()

    def before_acknowledge(self, broker, queue_name):
        """Called before a message is acknowledged.
        """

    def after_acknowledge(self, broker, queue_name):
        """Called after a message has been acknowledged.
        """

    def before_declare_actor(self, broker, actor):
        """Called before an actor is declared.
        """

    def after_declare_actor(self, broker, actor):
        """Called after an actor has been declared.
        """

    def before_declare_queue(self, broker, queue_name):
        """Called before a queue is declared.
        """

    def after_declare_queue(self, broker, queue_name):
        """Called before a queue has been declared.
        """

    def before_enqueue(self, broker, message, delay):
        """Called before a message is enqueued.
        """

    def after_enqueue(self, broker, message, delay):
        """Called after a message has been enqueued.
        """

    def before_process_message(self, broker, message):
        """Called before a message is processed.
        """

    def after_process_message(self, broker, message, *, result=None, exception=None):
        """Called after a message has been processed.
        """


class Retries(Middleware):
    """Middleware that automatically retries failed tasks with
    exponential backoff.

    Note:
      All paramters can be overwritten on a per-actor basis.

    Example:

      @dramatiq.actor(max_backoff=2000):
      def some_fn():
        pass

    Parameters:
      max_age(int): The maximum task age in milliseconds.
      max_retires(int): The maximum number of times tasks can be retried.
      min_backoff(int): The minimum amount of backoff (in
        milliseconds) to apply to retried tasks.
      max_backoff(int): The maximum amount of backoff (in
        milliseconds) to apply to retried tasks.
    """

    def __init__(self, *, max_age=None, max_retries=None, min_backoff=2000, max_backoff=3600000):
        self.logger = logging.getLogger("Retries")
        self.max_age = max_age
        self.max_retries = max_retries
        self.min_backoff = min_backoff
        self.max_backoff = max_backoff
        self.actor_options = set([
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
            return

        if max_age is not None and int(time() * 1000) - message.message_timestamp >= max_age:
            self.logger.warning("Message %r has exceeded its age limit.", message.message_id)
            return

        min_backoff = actor.options.get("min_backoff", self.min_backoff)
        max_backoff = actor.options.get("max_backoff", self.max_backoff)
        delay = min(min_backoff * 2 ** retries, max_backoff) / 2
        delay = int(delay + uniform(0, delay))
        self.logger.info("Retrying message %r in %d milliseconds.", message.message_id, delay)
        message.options["retries"] += 1
        broker.enqueue(message, delay=delay)
