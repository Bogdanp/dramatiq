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

from .broker import get_broker
from .result import Result


class CollectionResults:
    """Result of a group or pipeline, having result related methods

    Parameters:
      children(List[Result|CollectionResults]): A sequence of results of messages, groups or pipelines.
    """

    def __init__(self, children):
        self.children = list(children)

    def __len__(self):
        return len(self._message_ids)

    def asdict(self):
        result = []
        for child in self.children:
            result.append(child.asdict())
        return result

    @classmethod
    def from_dict(cls, group_results):
        children = []
        for result in group_results:
            if isinstance(result, list):
                child = cls.from_dict(result)
            else:
                child = Result(**result)
            children.append(child)
        return CollectionResults(children)

    @property
    def completed(self) -> bool:
        """Returns True when all the jobs have been
        completed.  Actors that don't store results are not counted,
        meaning this may be inaccurate if all or some of your actors
        don't store results.

        Raises:
          RuntimeError: If your broker doesn't have a result backend
            set up.
        """
        return self.completed_count == len(self)

    @property
    def _message_ids(self):
        message_ids = []
        for child in self.children:
            if isinstance(child, CollectionResults):
                message_ids += child._message_ids
            else:
                message_ids += [child.message_id]
        return message_ids

    @property
    def completed_count(self) -> int:
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
        broker = get_broker()
        backend = broker.get_result_backend()
        # we could use message.completed here but we just want to make 1 call to get_status
        return backend.get_status(self._message_ids)

    def get(self, *, block=False, timeout=None, raise_on_error=True, forget=False):
        """Get the results of each job in the collection.

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

            if isinstance(child, CollectionResults):
                results = child.get(block=block, timeout=timeout, raise_on_error=raise_on_error, forget=forget)
                yield list(results)
            else:
                yield child.get(block=block, timeout=timeout, raise_on_error=raise_on_error, forget=forget)

    def wait(self, *, timeout=None, raise_on_error=True, forget=False):
        """Block until all the jobs in the collection have finished or
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
