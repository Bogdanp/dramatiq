from ..common import current_millis
from ..logging import get_logger
from .middleware import Middleware


class AgeLimit(Middleware):
    """Middleware that drops messages that have been in the queue for
    too long.

    Parameters:
      age_limit(int): The default message age limit in millseconds.
        Defaults to ``None``, meaning that messages can exist
        indefinitely.
    """

    def __init__(self, *, age_limit=None):
        self.logger = get_logger(__name__, type(self))
        self.age_limit = None

    @property
    def actor_options(self):
        return set(["age_limit"])

    def before_process_message(self, broker, message):
        actor = broker.get_actor(message.actor_name)
        age_limit = actor.options.get("age_limit", self.age_limit)
        if not age_limit:
            return

        if current_millis() - message.message_timestamp >= age_limit:
            message.fail()
