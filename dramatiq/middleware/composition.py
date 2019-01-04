# This file is a part of Dramatiq.
#
# Copyright (C) 2017,2018 CLEARTYPE SRL <bogdan@cleartype.io>
#
# Dramatiq is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# Dramatiq is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from collections import namedtuple
from ..message import Message
from ..rate_limits import Barrier
from .middleware import Middleware


class GroupStart(namedtuple("GroupStart", ("id", "count"))):
    """Metadata required to start a group.

    Parameters:
      id(str): The id of the group to start.
      count(int): The number of items in the group.
    """

    def __new__(cls, *, id, count):
        assert count, "Empty groups are not supported. Yet."
        return super().__new__(cls, id=id, count=count)

    def asdict(self):
        return self._asdict()


class Composition(Middleware):
    """Middleware that can manage arbitrary compositions of messages.

    Parameters:
      backend(RateLimiterBackend): The rate limiter backend to use
        for managing group completion barriers.
      ttl(int): The maximum number of milliseconds group barriers
        may exist before they time out and the group fails.
    """

    def __init__(self, backend, ttl):
        self.backend = backend
        self.ttl = ttl

    @property
    def actor_options(self):
        # composition_group_ids: The group ids that must be confirmed
        #   completed in order for the targets or starts to be acted on.
        # composition_targets: The serialized messages that should be
        #   run when a message's groups have all completed.
        # composition_starts: The serialized representation of groups
        #   that should be started when a message's groups have all completed.
        return {
            "composition_group_ids",
            "composition_targets",
            "composition_starts",
        }

    def barrier(self, group_id):
        return Barrier(self.backend, group_id, ttl=self.ttl)

    def start_group(self, group_id, count):
        """Start the group expecting count messages."""
        return self.barrier(group_id).create(parties=count)

    def check_group(self, group_id):
        """Check if this is the last message in the group."""
        return self.barrier(group_id).wait(block=False)

    def process(self, *, broker, group_ids=(), starts=(), targets=()):
        # The group ids are given in the order they must resolve,
        # from the innermost group to the final outer group.
        # Only check outer groups when inner groups are finished.
        if all(self.check_group(group_id) for group_id in group_ids):
            for start in starts:
                self.start_group(start.id, start.count)
            for target in targets:
                broker.enqueue(target)

    def after_process_message(self, broker, message, *, result=None, exception=None):
        if exception is not None or message.failed:
            return

        group_ids = message.options.get('composition_group_ids', [])
        starts = [
            GroupStart(**start)
            for start in message.options.get('composition_starts', [])
        ]
        targets = [
            Message(**target)
            for target in message.options.get('composition_targets', [])
        ]
        self.process(
            broker=broker,
            group_ids=group_ids,
            starts=starts,
            targets=targets,
        )
