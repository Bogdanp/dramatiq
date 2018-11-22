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
from .broker import get_broker
from .composition_result import GroupResults, PipelineResult


class pipeline:
    """Chain actors together, passing the result of one actor to the
    next one in line.

    Parameters:
      children(Iterator[Message|pipeline]): A sequence of messages or
        pipelines.  Child pipelines are flattened into the resulting
        pipeline.
      broker(Broker): The broker to run the pipeline on.  Defaults to
        the current global broker.
    """

    def __init__(self, children, *, broker=None):
        self.broker = broker or get_broker()
        self.messages = messages = []

        for child in children:
            if isinstance(child, pipeline):
                for message in child.messages:
                    messages.append(message.copy())
            else:
                messages.append(child.copy())

        for message, next_message in zip(messages, messages[1:]):
            message.options["pipe_target"] = next_message.asdict()

    def __len__(self):
        """Returns the length of the pipeline.
        """
        return len(self.messages)

    def __or__(self, other):
        """Returns a new pipeline with "other" added to the end.
        """
        return type(self)(self.messages + [other])

    def __str__(self):  # pragma: no cover
        return "pipeline([%s])" % ", ".join(str(m) for m in self.messages)

    def run(self, *, delay=None):
        """Run this pipeline.

        Parameters:
          delay(int): The minimum amount of time, in milliseconds, the
            pipeline should be delayed by.

        Returns:
          pipeline: Itself.
        """
        self.broker.enqueue(self.messages[0], delay=delay)
        return self

    @property
    def result(self):
        """ PipelineResult created from this pipeline, used for result related methods"""
        return PipelineResult([message.result for message in self.messages])


class group:
    """Run a group of actors in parallel.

    Parameters:
      children(Iterator[Message|group|pipeline]): A sequence of
        messages, groups or pipelines.
      broker(Broker): The broker to run the group on.  Defaults to the
        current global broker.
    """

    def __init__(self, children, *, broker=None):
        self.children = list(children)
        self.broker = broker or get_broker()

    def __len__(self):
        """Returns the size of the group.
        """
        return len(self.children)

    def __str__(self):  # pragma: no cover
        return "group([%s])" % ", ".join(str(c) for c in self.children)

    def run(self, *, delay=None):
        """Run the actors in this group.

        Parameters:
          delay(int): The minimum amount of time, in milliseconds,
            each message in the group should be delayed by.
        """
        for child in self.children:
            if isinstance(child, (group, pipeline)):
                child.run(delay=delay)
            else:
                self.broker.enqueue(child, delay=delay)

        return self

    @property
    def results(self):
        """ GroupResults created from this group, used for result related methods"""
        children = []
        for child in self.children:
            if isinstance(child, group):
                children.append(child.results)
            else:
                children.append(child.result)
        return GroupResults(children=children)
