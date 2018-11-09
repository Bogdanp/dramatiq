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

from .broker import get_broker
from .results import ResultMissing


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
                messages.extend(message.copy() for message in child.messages)
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

    @property
    def completed(self):
        """Returns True when all the jobs in the pipeline have been
        completed.  This will always return False if the last actor in
        the pipeline doesn't store results.

       Raises:
          RuntimeError: If your broker doesn't have a result backend
            set up.
        """
        try:
            self.messages[-1].get_result()

            return True
        except ResultMissing:
            return False

    @property
    def completed_count(self):
        """Returns the total number of jobs that have been completed.
        Actors that don't store results are not counted, meaning this
        may be inaccurate if all or some of your actors don't store
        results.

        Raises:
          RuntimeError: If your broker doesn't have a result backend
            set up.

        Returns:
          int: The total number of results.
        """
        for count, message in enumerate(self.messages, start=1):
            try:
                message.get_result()
            except ResultMissing:
                return count - 1

        return count

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

    def get_result(self, *, block=False, timeout=None, raise_on_error=True):
        """Get the result of this pipeline.

        Pipeline results are represented by the result of the last
        message in the chain.

        Parameters:
          block(bool): Whether or not to block until a result is set.
          timeout(int): The maximum amount of time, in ms, to wait for
            a result when block is True.  Defaults to 10 seconds.
          raise_on_error(bool): raise an error if the result stored in
            an error

        Raises:
          ResultMissing: When block is False and the result isn't set.
          ResultTimeout: When waiting for a result times out.
          ErrorStored: When the result is an error and raise_on_error is True

        Returns:
          object: The result.
        """
        return self.messages[-1].get_result(block=block, timeout=timeout, raise_on_error=raise_on_error)

    def get_results(self, *, block=False, timeout=None, raise_on_error=True):
        """Get the results of each job in the pipeline.

        Parameters:
          block(bool): Whether or not to block until a result is set.
          timeout(int): The maximum amount of time, in ms, to wait for
            a result when block is True.  Defaults to 10 seconds.
          raise_on_error(bool): raise an error if the result stored in
            an error

        Raises:
          ResultMissing: When block is False and the result isn't set.
          ResultTimeout: When waiting for a result times out.
          ErrorStored: When the result is an error and raise_on_error is True

        Returns:
          A result generator.
        """
        deadline = None
        if timeout:
            deadline = time.monotonic() + timeout / 1000

        for message in self.messages:
            if deadline:
                timeout = max(0, int((deadline - time.monotonic()) * 1000))

            yield message.get_result(block=block, timeout=timeout, raise_on_error=raise_on_error)


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

    @property
    def completed(self):
        """Returns True when all the jobs in the group have been
        completed.  Actors that don't store results are not counted,
        meaning this may be inaccurate if all or some of your actors
        don't store results.

        Raises:
          RuntimeError: If your broker doesn't have a result backend
            set up.
        """
        return self.completed_count == len(self)

    @property
    def completed_count(self):
        """Returns the total number of jobs that have been completed.
        Actors that don't store results are not counted, meaning this
        may be inaccurate if all or some of your actors don't store
        results.

        Raises:
          RuntimeError: If your broker doesn't have a result backend
            set up.

        Returns:
          int: The total number of results.
        """
        for count, child in enumerate(self.children, start=1):
            try:
                if isinstance(child, group):
                    child.get_results()
                else:
                    child.get_result()
            except ResultMissing:
                return count - 1

        return count

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

    def get_results(self, *, block=False, timeout=None, raise_on_error=True):
        """Get the results of each job in the group.

        Parameters:
          block(bool): Whether or not to block until the results are stored.
          timeout(int): The maximum amount of time, in milliseconds,
            to wait for results when block is True.  Defaults to 10
            seconds.
          raise_on_error(bool): raise an error if the result stored in
            an error

        Raises:
          ResultMissing: When block is False and the results aren't set.
          ResultTimeout: When waiting for results times out.
          ErrorStored: When the result is an error and raise_on_error is True

        Returns:
          A result generator.
        """
        deadline = None
        if timeout:
            deadline = time.monotonic() + timeout / 1000

        for child in self.children:
            if deadline:
                timeout = max(0, int((deadline - time.monotonic()) * 1000))

            if isinstance(child, group):
                yield list(child.get_results(block=block, timeout=timeout, raise_on_error=raise_on_error))
            else:
                yield child.get_result(block=block, timeout=timeout, raise_on_error=raise_on_error)

    def wait(self, *, timeout=None, raise_on_error=True):
        """Block until all the jobs in the group have finished or
        until the timeout expires.

        Parameters:
          timeout(int): The maximum amount of time, in ms, to wait.
            Defaults to 10 seconds.
          raise_on_error(bool): raise an error if one of the result stored in
            an error
        """
        for _ in self.get_results(block=True, timeout=timeout, raise_on_error=raise_on_error):  # pragma: no cover
            pass
