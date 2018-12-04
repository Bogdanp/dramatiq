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
from .composition_result import CollectionResults
from .errors import ResultNotStored


class GroupInfo(namedtuple("GroupInfo", ("group_id", "count", "results"))):
    """Encapsulates metadata about a group being sent to multiple actors.

    Parameters:
      group_id(str): The id of the group
      count(int): The number of child in the group
      results(CollectionResults)
    """

    def __new__(cls, *, group_id: str, count: int, results: CollectionResults):
        return super().__new__(cls, group_id, count, results)

    def asdict(self):
        return {
            'group_id': self.group_id,
            'count': self.count,
            'results': self.results.asdict() if self.results else None
        }

    @staticmethod
    def from_dict(group_id, count, results):
        results = CollectionResults.from_dict(results) if results else None
        return GroupInfo(group_id=group_id, count=count, results=results)


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

    def build(self, *, last_options=None):
        """ Build the pipeline, return the first message to be enqueued or integrated in another pipeline

        Build the pipeline by starting at the end. We build a message with all it's options in one step and
        we serialize it (asdict) as the previous message pipe_target in the next step.

        We need to know what is the options (pipe_target) of the pipeline before building it because we cannot
        edit the pipeline after it has been built.

        Parameters:
            last_options(dict): options to be assigned to the last actor of the pipeline (ex: pipe_target)

        Returns:
            the first message of the pipeline
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

            next_child = child.build(options)

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
        first = self.build()
        if isinstance(first, list):
            for message in first:
                self.broker.enqueue(message, delay=delay)
        else:
            self.broker.enqueue(first, delay=delay)
        return self

    @property
    def results(self) -> CollectionResults:
        """ CollectionResults created from this pipeline, used for result related methods"""
        results = []
        for element in self.children:
            results += [element.results if isinstance(element, group) else element.result]
        return CollectionResults(results)

    @property
    def result(self):
        """ Result of the last message/group of the pipeline"""
        last_child = self.children[-1]
        return last_child.results if isinstance(last_child, group) else last_child.result


class group:
    """Run a group of actors in parallel.

    Parameters:
      children(Iterator[Message|pipeline]): A sequence of messages or pipelines.
      broker(Broker): The broker to run the group on.  Defaults to the current global broker.

    Attributes:
        children(List[Message|pipeline]) The sequence to execute as a group
    """

    def __init__(self, children, *, broker=None, group_id=None):
        self.children = []
        for child in children:
            if isinstance(child, group):
                raise ValueError('Groups of groups are not supported')
            self.children.append(child)

        self.broker = broker or get_broker()
        self.group_id = generate_unique_id() if group_id is None else group_id

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

    def build(self, options):
        """ Build group for pipeline """
        options = {'group_info': self.info.asdict(), **options}
        messages = []
        for group_child in self.children:
            if isinstance(group_child, pipeline):
                first = group_child.build(last_options=options)
                messages += [first]
            else:
                messages += [group_child.build(options)]
        return messages

    @property
    def info(self):
        """ Info used for group completion """
        try:
            results = self.results
        except ResultNotStored:
            results = None
        return GroupInfo(group_id=self.group_id, count=len(self.children), results=results)

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
    def results(self) -> CollectionResults:
        """ CollectionResults created from this group, used for result related methods"""
        return CollectionResults(children=[child.result for child in self.children])
