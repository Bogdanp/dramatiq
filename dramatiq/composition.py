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
from copy import deepcopy

from .broker import get_broker
from .middleware.group_callbacks import GROUP_CALLBACK_BARRIER_TTL, GroupCallbacks
from .rate_limits import Barrier
from .results import ResultMissing

if TYPE_CHECKING:
    from .message import Message


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
    _messages: list[Message]

    def __init__(self, children: Iterable[Message | pipeline | group], *, broker=None):
        self.broker = broker or get_broker()
        self.steps = children

        self.rate_limiter_backend = None
        for middleware in self.broker.middleware:
            if isinstance(middleware, GroupCallbacks):
                self.rate_limiter_backend = middleware.rate_limiter_backend
                break
        self._messages = self.generate_messages()


    def generate_messages(self) -> list[tuple[Message]]:
        messages = []
        for child, next_child in zip(self.steps, self.steps[1:] + [None]):

            if isinstance(child, pipeline):
                messages.extend(child.generate_messages())

            elif isinstance(child, group):
                if next_child is not None:
                    child.add_completion_callback(next_child)
                group_messages = child.generate_messages()
                messages.append(tuple(group_messages))

            else:
                # assumed to be a Message
                messages.append((child,))
        for message_tup, next_message_tup in zip(messages, messages[1:]):
            if len(message_tup) > 1:
                # we add completion callbacks inside run method
                continue
            message_dicts = [message.asdict() for message in next_message_tup]
            message_tup[0].options["pipe_targets"] = message_dicts

        return messages

    def __len__(self):
        """Returns the length of the pipeline.
        """
        return len(self.steps)

    def __or__(self, other):
        """Returns a new pipeline with "other" added to the end.
        """
        return type(self)(self.steps + [other], broker=self.broker)

    def __str__(self):  # pragma: no cover
        return "pipeline([%s])" % ", ".join(str(m) for m in self._messages)

    @property
    def completed(self):
        """Returns True when all the jobs in the pipeline have been
        completed.  This will always return False if the last actor in
        the pipeline doesn't store results.

       Raises:
          RuntimeError: If your broker doesn't have a result backend
            set up.
        """
        if isinstance(self.steps[-1], group):
            return self.steps[-1].completed
        try:
            self.steps[-1].get_result()

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
        for count, message in enumerate(self.steps, start=1):
            if isinstance(message, group):
                if not message.completed:
                    return count - 1
            else:
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
        self._messages = self.generate_messages()
        max_message_delay = max(
            message.options.get("delay") or 0 for message in self._messages[0]
        )
        delay = max(delay or 0, max_message_delay) or None

        for message in self._messages[0]:
            self.broker.enqueue(message, delay=delay)
        for step in self.steps:
            step.remove_group_completion_uuids()
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
        last_message = self.steps[-1]
        if isinstance(last_message, group):
            raise RuntimeError("Pipelines ending in groups can't return a single result. Call get_results instead.")

        if isinstance(last_message, pipeline):
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

        backend = self.broker.get_results_backend()
        for messages in self._messages:
            if deadline:
                timeout = max(0, int((deadline - time.monotonic()) * 1000))

            for message in messages:
                yield message.get_result(backend=backend, block=block, timeout=timeout)

    def set_completion_uuid_and_callbacks(self, uuid, callbacks):
        for msg in self._messages[-1]:
            msg.set_completion_uuid_and_callbacks(uuid, callbacks)

    def remove_group_completion_uuids(self):
        if isinstance(self.steps[-1], (group, pipeline)):
            self.steps[-1].remove_completion_uuids()


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
        self.completion_callbacks = dict()
        self.completion_uuid = None

        self.rate_limiter_backend = None
        for middleware in self.broker.middleware:
            if isinstance(middleware, GroupCallbacks):
                self.rate_limiter_backend = middleware.rate_limiter_backend
                break

    def __len__(self):
        """Returns the size of the group.
        """
        return len(self.children)

    def __str__(self):  # pragma: no cover
        return "group([%s])" % ", ".join(str(c) for c in self.children)

    def __or__(self, other) -> pipeline:
        """Combine this message into a pipeline with "other".
        """
        return pipeline([self, other])

    def add_completion_callback(self, message: Message | pipeline | group):
        """Adds a completion callback to run once every job in this
        group has completed.  Each group may have multiple completion
        callbacks.

        Warning:
          This functionality is dependent upon the GroupCallbacks
          middleware.  If that's not set up correctly, then calling
          run after adding a callback will raise a RuntimeError.

        Parameters:
          message(Message)
        """

        if self.rate_limiter_backend is None:
            raise RuntimeError(
                "GroupCallbacks middleware not found! Did you forget "
                "to set it up? It is required if you want to use "
                "group callbacks."
            )
        if isinstance(message, pipeline):
            for m in message.generate_messages():
                self.completion_callbacks[m.message_id] = m.asdict()
                if isinstance(m, pipeline):
                    break
        else:
            self.completion_callbacks[message.message_id] = message.asdict()

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
        for message in self.generate_messages():
            self.broker.enqueue(message, delay=delay)
        self.completion_uuid = None
        return self

    def generate_messages(self, ) -> list[Message]:
        messages = []
        if self.completion_callbacks and not self.completion_uuid:
            # Generate a new completion uuid on every run so that if a
            # group is re-run, the barriers are all separate.
            # Re-using a barrier's name is an unsafe operation.
            completion_uuid = str(uuid4())
            completion_barrier = Barrier(self.rate_limiter_backend, completion_uuid, ttl=GROUP_CALLBACK_BARRIER_TTL)
            completion_barrier.create(self.get_barrier_number())
            self.completion_uuid = completion_uuid

        for child in self.children:
            if isinstance(child, group):
                messages.extend(child.generate_messages())

            elif isinstance(child, pipeline):
                messages.extend(child.generate_messages()[0])
            else:
                messages.append(child)
            if self.completion_callbacks:
                try:
                    child.set_completion_uuid_and_callbacks(self.completion_uuid, self.completion_callbacks)
                except:
                    breakpoint()
        return messages

    def get_barrier_number(self) -> list[Message | pipeline]:

        num_tasks = 0
        for child in self.children:
            if isinstance(child, group):
                # groups within groups get flattened
                num_tasks += child.get_barrier_number()
            elif isinstance(child, pipeline) and isinstance(child.steps[-1], group):
                num_tasks += child.steps[-1].get_barrier_number()
            else:
                num_tasks += 1

        return num_tasks

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

    def set_completion_uuid_and_callbacks(self, uuid, callbacks):
        for child in self.children:
            child.set_completion_uuid_and_callbacks(uuid, callbacks)

    def remove_group_completion_uuids(self):
        self.completion_uuid = None
        for child in self.children:
            child.remove_group_completion_uuids()
