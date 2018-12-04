# This file is a part of Remoulade.
#
# Copyright (C) 2017,2018 CLEARTYPE SRL <bogdan@cleartype.io>
#
# Remoulade is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# Remoulade is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import time
from collections import namedtuple

from .broker import get_broker
from .common import generate_unique_id
from .composition import pipeline
from .encoder import Encoder, JSONEncoder
from .errors import ResultNotStored
from .result import Result

#: The global encoder instance.
global_encoder = JSONEncoder()


def get_encoder() -> Encoder:
    """Get the global encoder object.

    Returns:
      Encoder
    """
    global global_encoder
    return global_encoder


def set_encoder(encoder: Encoder):
    """Set the global encoder object.

    Parameters:
      encoder(Encoder): The encoder instance to use when serializing
        messages.
    """
    global global_encoder
    global_encoder = encoder


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

    def __or__(self, other) -> pipeline:
        """Combine this message into a pipeline with "other".
        """
        return pipeline([self, other])

    def asdict(self):
        """Convert this message to a dictionary.
        """
        return self._asdict()

    @classmethod
    def decode(cls, data):
        """Convert a bytestring to a message.
        """
        return cls(**global_encoder.decode(data))

    def encode(self):
        """Convert this message to a bytestring.
        """
        return global_encoder.encode(self._asdict())

    def copy(self, **attributes):
        """Create a copy of this message.
        """
        updated_options = attributes.pop("options", {})
        options = self.options.copy()
        options.update(updated_options)
        return self._replace(**attributes, options=options)

    def build(self, options):
        """ Build message for pipeline """
        return self.copy(options=options)

    @property
    def result(self):
        broker = get_broker()
        actor = broker.get_actor(actor_name=self.actor_name)
        if not actor.options.get('store_results'):
            raise ResultNotStored('There cannot be any result to an actor without store_results=True')
        return Result(message_id=self.message_id)

    def __str__(self):
        return "%s / %s" % (self.actor_name, self.message_id)
