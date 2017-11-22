import json
import time
import uuid

from collections import namedtuple

from .broker import get_broker
from .results import Results


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

    def get_result(self, *, backend=None, block=False, timeout=None):
        """Get the result associated with this message from a result
        backend.

        Warning:
          If you use multiple result backends or brokers you should
          always pass the backend parameter.  This method is only able
          to infer the result backend off of the default broker.

        Parameters:
          backend(ResultBackend): The result backend to use to get the
            result.  If omitted, this method will try to find and use
            the result backend on the default broker instance.
          block(bool): Whether or not to block while waiting for a
            result.
          timeout(int): The maximum amount of time, in ms, to block
            while waiting for a result.

        Raises:
          RuntimeError: If there is no result backend on the default
            broker.
          ResultMissing: When block is False and the result isn't set.
          ResultTimeout: When waiting for a result times out.

        Returns:
          object: The result.
        """
        if not backend:
            broker = get_broker()
            for middleware in broker.middleware:
                if isinstance(middleware, Results):
                    backend = middleware.backend
                    break
            else:
                raise RuntimeError("The default broker doesn't have a results backend.")

        return backend.get_result(self, block=block, timeout=timeout)

    def __str__(self):
        params = ", ".join(repr(arg) for arg in self.args)
        if self.kwargs:
            params += ", " if params else ""
            params += ", ".join("%s=%r" % (name, value) for name, value in self.kwargs.items())

        return "%s(%s)" % (self.actor_name, params)
