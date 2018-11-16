# This file is a part of Remoulade.
#
# Copyright (C) 2017,2018 WIREMIND SAS <dev@wiremind.fr>
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
from collections import deque

from .results import ResultMissing


class PipelineResult:
    """ Result of a pipeline, having result related methods

    Parameters:
      results(List[AsyncResult]): results of the pipeline
    """

    def __init__(self, results):
        self.results = results

    def __len__(self):
        """Returns the length of the pipeline."""
        return len(self.results)

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
            self.results[-1].get()

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
        for count, result in enumerate(self.results, start=1):
            try:
                result.get()
            except ResultMissing:
                return count - 1

        return count

    def get(self, *, block=False, timeout=None, raise_on_error=True, forget=False):
        """Get the result of the pipeline.

        Pipeline results are represented by the result of the last
        message in the chain.

        Parameters:
          block(bool): Whether or not to block until a result is set.
          timeout(int): The maximum amount of time, in ms, to wait for
            a result when block is True.  Defaults to 10 seconds.
          raise_on_error(bool): raise an error if the result stored in
            an error
          forget(bool): if true the result is discarded from the result
            backend

        Raises:
          ResultMissing: When block is False and the result isn't set.
          ResultTimeout: When waiting for a result times out.
          ErrorStored: When the result is an error and raise_on_error is True

        Returns:
          object: The result.
        """
        if forget:
            results = list(self.get_all(block=block, timeout=timeout, raise_on_error=raise_on_error, forget=True))
            return results[-1]
        return self.results[-1].get(block=block, timeout=timeout, raise_on_error=raise_on_error, forget=False)

    def get_all(self, *, block=False, timeout=None, raise_on_error=True, forget=False):
        """Get the results of each job in the pipeline.

        Parameters:
          block(bool): Whether or not to block until a result is set.
          timeout(int): The maximum amount of time, in ms, to wait for
            a result when block is True.  Defaults to 10 seconds.
          raise_on_error(bool): raise an error if the result stored in
            an error
          forget(bool): if true the result is discarded from the result
            backend

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

        for result in self.results:
            if deadline:
                timeout = max(0, int((deadline - time.monotonic()) * 1000))

            yield result.get(block=block, timeout=timeout, raise_on_error=raise_on_error, forget=forget)


class GroupResults:
    """Result of a group, having result related methods

    Parameters:
      children(List[AsyncResult|GroupResults|PipelineResult]): A sequence of results of
        messages, groups or pipelines.
    """

    def __init__(self, children):
        self.children = list(children)

    def __len__(self):
        return len(self.children)

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
        count = 0
        for count, child in enumerate(self.children, start=1):
            try:
                child.get()
            except ResultMissing:
                return count - 1

        return count

    def get(self, *, block=False, timeout=None, raise_on_error=True, forget=False):
        """Get the results of each job in the group.

        Parameters:
          block(bool): Whether or not to block until the results are stored.
          timeout(int): The maximum amount of time, in milliseconds,
            to wait for results when block is True.  Defaults to 10
            seconds.
          raise_on_error(bool): raise an error if the result stored in
            an error
          forget(bool): if true the result is discarded from the result
            backend

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

            if isinstance(child, GroupResults):
                results = child.get(block=block, timeout=timeout, raise_on_error=raise_on_error, forget=forget)
                yield list(results)
            else:
                yield child.get(block=block, timeout=timeout, raise_on_error=raise_on_error, forget=forget)

    def wait(self, *, timeout=None, raise_on_error=True, forget=False):
        """Block until all the jobs in the group have finished or
        until the timeout expires.

        Parameters:
          timeout(int): The maximum amount of time, in ms, to wait.
            Defaults to 10 seconds.
          raise_on_error(bool): raise an error if one of the result stored in
            an error
          forget(bool): if true the result is discarded from the result
            backend
        """
        iterator = self.get(block=True, timeout=timeout, raise_on_error=raise_on_error, forget=forget)
        # Consume the iterator (https://docs.python.org/3/library/itertools.html#itertools-recipes)
        deque(iterator, maxlen=0)
