import json
import time
import uuid

from collections import namedtuple


def generate_unique_id():
    return str(uuid.uuid4())


class Message(namedtuple("Message", (
        "queue_name", "actor_name", "args", "kwargs",
        "options", "message_id", "message_timestamp",
))):
    """Encapsulates metadata about messages being sent to individual actors.

    Parameters:
      queue_name(str): The name of the queue the message belogns to.
      actor_name(str): The name of the actor that will receive the message.
      args(tuple): Positional arguments that are passed to the actor.
      kwargs(dict): Keyword arguments that are passed to the actor.
      options(dict): Arbitrary options passed to the broker and middleware.
      message_id(str): A globally-unique id assigned to the actor.
      message_timestamp(int): The UNIX timestamp in milliseconds
        representing when the message was first enqueued.
    """

    def __new__(cls, *, queue_name, actor_name, args, kwargs, options, message_id=None, message_timestamp=None):
        return super().__new__(
            cls, queue_name, actor_name, tuple(args), kwargs, options,
            message_id=message_id or generate_unique_id(),
            message_timestamp=message_timestamp or int(time.time() * 1000),
        )

    @classmethod
    def decode(cls, data):
        """Convert a JSON bytestring to a message.
        """
        return cls(**json.loads(data.decode("utf-8")))

    def encode(self):
        """Convert this message to a JSON bytestring.
        """
        return json.dumps(self._asdict(), separators=(",", ":")).encode("utf-8")

    def copy(self, **attributes):
        """Create a copy of this message.
        """
        updated_options = attributes.pop("options", {})
        options = self.options.copy()
        options.update(updated_options)
        return self._replace(**attributes, options=options)

    def __str__(self):
        params = ", ".join(repr(arg) for arg in self.args)
        if self.kwargs:
            params += ", " if params else ""
            params += ", ".join(f"{name}={value!r}" for name, value in self.kwargs.items())

        return f"{self.actor_name}({params})"
