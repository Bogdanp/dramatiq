from ..common import current_millis
from ..logging import get_logger
from .middleware import Middleware


class AgeLimit(Middleware):
    """Middleware that drops messages that have been in the queue for
    too long.

    Parameters:
      max_age(int): The default message age limit in millseconds.
        Defaults to ``None``, meaning that messages can exist
        indefinitely.
    """

    def __init__(self, *, max_age=None):
        self.logger = get_logger(__name__, type(self))
        self.max_age = None

    @property
    def actor_options(self):
        return set(["max_age"])

    def before_process_message(self, broker, message):
        actor = broker.get_actor(message.actor_name)
        max_age = actor.options.get("max_age", self.max_age)
        if not max_age:
            return

        if current_millis() - message.message_timestamp >= max_age:
            self.logger.warning("Message %r has exceeded its age limit.", message.message_id)
            message.fail()
            return
