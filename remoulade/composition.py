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
from collections import namedtuple

from .broker import get_broker
from .common import generate_unique_id
from .composition_result import GroupResults, PipelineResult


class GroupInfo(namedtuple("GroupInfo", ("group_id", "count", "results"))):
    """Encapsulates metadata about a group being sent to multiple actors.

    Parameters:
      group_id(str): The id of the group
      count(int): The number of child in the group
      results(GroupResults)
    """

    def __new__(cls, *, group_id: str, count: int, results: GroupResults):
        return super().__new__(cls, group_id, count, results)

    def asdict(self):
        return {
            'group_id': self.group_id,
            'count': self.count,
            'results': self.results.asdict()
        }

    @staticmethod
    def from_dict(group_id, count, results):
        return GroupInfo(group_id=group_id, count=count, results=GroupResults.from_dict(results))


class pipeline:
    """Chain actors together, passing the result of one actor to the
    next one in line.

    Parameters:
      children(Iterator[Message|pipeline|group]): A sequence of messages or
        pipelines or groups.  Child pipelines are flattened into the resulting
        pipeline.
      broker(Broker): The broker to run the pipeline on.  Defaults to
        the current global broker.

    Attributes:
        children(List[Message|group]) The sequence of messages or groups to execute as a pipeline
    """

    def __init__(self, children, *, broker=None):
        self.broker = broker or get_broker()

        self.children = []
        for child in children:
            if isinstance(child, pipeline):
                self.children += child.children
            elif isinstance(child, group):
                self.children.append(child)
            else:
                self.children.append(child.copy())

    def _build(self, *, last_options=None):
        """ Build the pipeline, return the first message to be enqueued or integrated in another pipeline

        Build the pipeline by starting at the end. We build a message with all it's options in one step and
        we serialize it (asdict) as the previous message pipe_target in the next step.

        We need to know what is the options (pipe_target) of the pipeline before building it because we cannot
        edit the pipeline after it has been built.

        Parameters:
            last_options(dict): options to be assigned to the last actor of the pipeline (ex: pipe_target)

        :param last_options:
        :return: the first message of the pipeline
        """
        next_child = None
        for child in reversed(self.children):
            if next_child:
                if isinstance(next_child, list):
                    options = {'pipe_target': [m.asdict() for m in next_child]}
                else:
                    options = {'pipe_target': next_child.asdict()}
            else:
                options = last_options or {}

            if isinstance(child, group):
                options = {'group_info': child.info.asdict(), **options}
                messages = []
                for group_child in child.children:
                    if isinstance(group_child, pipeline):
                        first = group_child._build(last_options=options)
                        messages += [first]
                    else:
                        messages += [group_child.copy(options=options)]
                next_child = messages
            else:
                next_child = child.copy(options=options)

        return next_child

    def __len__(self):
        """Returns the length of the pipeline.
        """
        return len(self.children)

    def __or__(self, other):
        """Returns a new pipeline with "other" added to the end.
        """
        return type(self)(self.children + [other])

    def __str__(self):  # pragma: no cover
        return "pipeline([%s])" % ", ".join(str(m) for m in self.children)

    def run(self, *, delay=None):
        """Run this pipeline.

        Parameters:
          delay(int): The minimum amount of time, in milliseconds, the
            pipeline should be delayed by.

        Returns:
          pipeline: Itself.
        """
        first = self._build()
        if isinstance(first, list):
            for message in first:
                self.broker.enqueue(message, delay=delay)
        else:
            self.broker.enqueue(first, delay=delay)
        return self

    @property
    def result(self) -> PipelineResult:
        """ PipelineResult created from this pipeline, used for result related methods"""
        results = []
        for element in self.children:
            results += [element.results if isinstance(element, group) else element.result]
        return PipelineResult(results)

    # TODO: think here
    # @property
    # def result(self):
    #     return self.children[-1]


class group:
    """Run a group of actors in parallel.

    Parameters:
      children(Iterator[Message|pipeline]): A sequence of messages or pipelines.
      broker(Broker): The broker to run the group on.  Defaults to the current global broker.

    Attributes:
        children(List[Message|pipeline]) The sequence to execute as a group
    """

    def __init__(self, children, *, broker=None, group_id=None):
        self.children = list(children)

        self.broker = broker or get_broker()
        self.group_id = generate_unique_id() if group_id is None else group_id
        self.info = GroupInfo(group_id=self.group_id, count=len(self.children), results=self.results)

    def __or__(self, other) -> pipeline:
        """Combine this group into a pipeline with "other".
        """
        return pipeline([self, other])

    def __len__(self) -> int:
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
            if isinstance(child, pipeline):
                child.run(delay=delay)
            else:
                self.broker.enqueue(child, delay=delay)

        return self

    @property
    def results(self) -> GroupResults:
        """ GroupResults created from this group, used for result related methods"""
        return GroupResults(children=[child.result for child in self.children])
