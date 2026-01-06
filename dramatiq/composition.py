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
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Iterable
from uuid import uuid4

from .broker import get_broker
from .rate_limits import Barrier
from .results import ResultMissing

if TYPE_CHECKING:
    from .message import Message


class pipeline:
    """Chain actors together, passing the result of one actor to the
    next one in line.

    Parameters:
      children(Iterable[Message|pipeline]): A sequence of messages or
        pipelines.  Child pipelines are flattened into the resulting
        pipeline.
      broker(Broker): The broker to run the pipeline on.  Defaults to
        the current global broker.
    """

    messages: list[Message]

    def __init__(self, children: Iterable[Message | pipeline], *, broker=None):
        self.broker = broker or get_broker()
        messages: list[Message]
        self.messages = messages = []

        for child in children:
            if isinstance(child, pipeline):
                messages.extend(message.copy() for message in child.messages)
            else:
                messages.append(child.copy())

        for message, next_message in zip(messages, messages[1:]):
            message.options["pipe_target"] = next_message.asdict()

    def __len__(self):
        """Returns the length of the pipeline."""
        return len(self.messages)

    def __or__(self, other):
        """Returns a new pipeline with "other" added to the end."""
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
            pipeline should be delayed by. If both pipeline's delay and
            first message's delay are provided, the bigger value will be
            used.

        Returns:
          pipeline: Itself.
        """
        delay = max(delay or 0, self.messages[0].options.get("delay") or 0) or None
        self.broker.enqueue(self.messages[0], delay=delay)
        return self

    def get_result(self, *, block=False, timeout=None):
        """Get the result of this pipeline.

        Pipeline results are represented by the result of the last
        message in the chain.

        Parameters:
          block(bool): Whether or not to block until a result is set.
          timeout(int): The maximum amount of time, in ms, to wait for
            a result when block is True.  Defaults to 10 seconds.

        Raises:
          ResultMissing: When block is False and the result isn't set.
          ResultTimeout: When waiting for a result times out.

        Returns:
          object: The result.
        """
        last_message = self.messages[-1]

        if isinstance(last_message, (group, pipeline)):
            return last_message.get_result(block=block, timeout=timeout)

        backend = self.broker.get_results_backend()
        return last_message.get_result(backend=backend, block=block, timeout=timeout)

    def get_results(self, *, block=False, timeout=None):
        """Get the results of each job in the pipeline.

        Parameters:
          block(bool): Whether or not to block until a result is set.
          timeout(int): The maximum amount of time, in ms, to wait for
            a result when block is True.  Defaults to 10 seconds.

        Raises:
          ResultMissing: When block is False and the result isn't set.
          ResultTimeout: When waiting for a result times out.

        Returns:
          A result generator.
        """
        deadline = None
        if timeout:
            deadline = time.monotonic() + timeout / 1000

        for message in self.messages:
            if deadline:
                timeout = max(0, int((deadline - time.monotonic()) * 1000))

            if isinstance(message, (group, pipeline)):
                yield message.get_result(block=block, timeout=timeout)

            backend = self.broker.get_results_backend()
            yield message.get_result(backend=backend, block=block, timeout=timeout)


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
        self.completion_callbacks = []

    def __len__(self):
        """Returns the size of the group."""
        return len(self.children)

    def __str__(self):  # pragma: no cover
        return "group([%s])" % ", ".join(str(c) for c in self.children)

    def add_completion_callback(self, message):
        """Adds a completion callback to run once every job in this
        group has completed.  Each group may have multiple completion
        callbacks.

        Warning:
          This functionality is dependent upon the optional |GroupCallbacks|
          middleware.  If that's not set up correctly, then calling
          run after adding a callback will raise a RuntimeError.

        Parameters:
          message(Message)
        """
        self.completion_callbacks.append(message.asdict())

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

        Returns:
          group: This same group.
        """
        if self.completion_callbacks:
            from .middleware.group_callbacks import (
                GROUP_CALLBACK_BARRIER_TTL,
                GroupCallbacks,
            )

            rate_limiter_backend = None
            for middleware in self.broker.middleware:
                if isinstance(middleware, GroupCallbacks):
                    rate_limiter_backend = middleware.rate_limiter_backend
                    break
            else:
                raise RuntimeError(
                    "GroupCallbacks middleware not found! Did you forget "
                    "to set it up? It is required if you want to use "
                    "group callbacks."
                )

            # Generate a new completion uuid on every run so that if a
            # group is re-run, the barriers are all separate.
            # Re-using a barrier's name is an unsafe operation.
            completion_uuid = str(uuid4())
            completion_barrier = Barrier(rate_limiter_backend, completion_uuid, ttl=GROUP_CALLBACK_BARRIER_TTL)
            completion_barrier.create(len(self.children))

            children = []
            for child in self.children:
                if isinstance(child, group):
                    raise NotImplementedError

                elif isinstance(child, pipeline):
                    pipeline_children = child.messages[:]
                    pipeline_children[-1] = pipeline_children[-1].copy(
                        options={
                            "group_completion_uuid": completion_uuid,
                            "group_completion_callbacks": self.completion_callbacks,
                        }
                    )

                    children.append(pipeline(pipeline_children, broker=child.broker))

                else:
                    children.append(
                        child.copy(
                            options={
                                "group_completion_uuid": completion_uuid,
                                "group_completion_callbacks": self.completion_callbacks,
                            }
                        )
                    )
        else:
            children = self.children

        for child in children:
            if isinstance(child, (group, pipeline)):
                child.run(delay=delay)
            else:
                self.broker.enqueue(child, delay=delay)

        return self

    def get_results(self, *, block=False, timeout=None):
        """Get the results of each job in the group.

        Parameters:
          block(bool): Whether or not to block until the results are stored.
          timeout(int): The maximum amount of time, in milliseconds,
            to wait for results when block is True.  Defaults to 10
            seconds.

        Raises:
          ResultMissing: When block is False and the results aren't set.
          ResultTimeout: When waiting for results times out.

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
                yield list(child.get_results(block=block, timeout=timeout))
            elif isinstance(child, pipeline):
                yield child.get_result(block=block, timeout=timeout)
            else:
                backend = self.broker.get_results_backend()
                yield child.get_result(backend=backend, block=block, timeout=timeout)

    def wait(self, *, timeout=None):
        """Block until all the jobs in the group have finished or
        until the timeout expires.

        Parameters:
          timeout(int): The maximum amount of time, in ms, to wait.
            Defaults to 10 seconds.

        Raises:
          ResultTimeout: When waiting times out.
        """
        for _ in self.get_results(block=True, timeout=timeout):  # pragma: no cover
            pass
