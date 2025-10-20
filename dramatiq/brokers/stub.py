# This file is a part of Dramatiq.
#
# Copyright (C) 2017,2018,2019,2020 CLEARTYPE SRL <bogdan@cleartype.io>
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
from collections import defaultdict
from itertools import chain
from queue import Empty, Queue
from typing import Optional

from ..broker import Broker, Consumer, MessageProxy
from ..common import current_millis, dq_name, iter_queue, join_queue
from ..errors import QueueNotFound
from ..message import Message
from ..middleware import Middleware


class StubBroker(Broker):
    """A broker that can be used within unit tests.

    Parameters:
      middleware: See :class:`Broker<dramatiq.Broker>`.
      fail_fast_default: Specifies the default value for the ``fail_fast``
        argument of :meth:`join<dramatiq.brokers.stub.StubBroker.join>`.
    """

    def __init__(self, middleware: Optional[list[Middleware]] = None, *, fail_fast_default: bool = True):
        super().__init__(middleware)

        self.dead_letters_by_queue: defaultdict[str, list[MessageProxy]] = defaultdict(list)
        self.fail_fast_default: bool = fail_fast_default

    @property
    def dead_letters(self) -> list[MessageProxy]:
        """The dead-lettered messages for all defined queues."""
        return [message for messages in self.dead_letters_by_queue.values() for message in messages]

    def consume(self, queue_name: str, prefetch: int = 1, timeout: int = 100) -> Consumer:
        """Create a new consumer for a queue.

        Parameters:
          queue_name(str): The queue to consume.
          prefetch(int): The number of messages to prefetch.
          timeout(int): The idle timeout in milliseconds.

        Raises:
          QueueNotFound: If the queue hasn't been declared.

        Returns:
          Consumer: A consumer that retrieves messages from Redis.
        """
        try:
            return _StubConsumer(
                self.queues[queue_name],
                self.dead_letters_by_queue[queue_name],
                timeout,
            )
        except KeyError:
            raise QueueNotFound(queue_name) from None

    def declare_queue(self, queue_name: str) -> None:
        """Declare a queue.  Has no effect if a queue with the given
        name has already been declared.

        Parameters:
          queue_name(str): The name of the new queue.
        """
        if queue_name in self.queues:
            return

        self.emit_before("declare_queue", queue_name)
        self.queues[queue_name] = Queue()
        self.emit_after("declare_queue", queue_name)

        delayed_name = dq_name(queue_name)
        self.queues[delayed_name] = Queue()
        self.delay_queues.add(delayed_name)
        self.emit_after("declare_delay_queue", delayed_name)

    def enqueue(self, message: Message, *, delay: Optional[int] = None) -> Message:
        """Enqueue a message.

        Parameters:
          message(Message): The message to enqueue.
          delay(int): The minimum amount of time, in milliseconds, to
            delay the message by.

        Raises:
          QueueNotFound: If the queue the message is being enqueued on
            doesn't exist.
        """
        queue_name = message.queue_name
        if delay is not None:
            queue_name = dq_name(queue_name)
            message_eta = current_millis() + delay
            message = message.copy(
                queue_name=queue_name,
                options={
                    "eta": message_eta,
                },
            )

        if queue_name not in self.queues:
            raise QueueNotFound(queue_name)

        self.emit_before("enqueue", message, delay)
        self.queues[queue_name].put(message.encode())
        self.emit_after("enqueue", message, delay)
        return message

    def flush(self, queue_name: str) -> None:
        """Drop all the messages from a queue.

        Parameters:
          queue_name(str): The queue to flush.
        """
        for _ in iter_queue(self.queues[queue_name]):
            self.queues[queue_name].task_done()

    def flush_all(self) -> None:
        """Drop all messages from all declared queues."""
        for queue_name in chain(self.queues, self.delay_queues):
            self.flush(queue_name)

        self.dead_letters_by_queue.clear()

    def join(self, queue_name: str, *, timeout: Optional[int] = None, fail_fast: Optional[bool] = None) -> None:
        """Wait for all the messages on the given queue to be
        processed.  This method is only meant to be used in tests
        to wait for all the messages in a queue to be processed.

        Raises:
          QueueJoinTimeout: When the timeout elapses.
          QueueNotFound: If the given queue was never declared.

        Parameters:
          queue_name(str): The queue to wait on.
          fail_fast(bool): When this is True and any message gets
            dead-lettered during the join, then an exception will be
            raised. When False, no exception will be raised.
            Defaults to None, which means use the value of the
            ``fail_fast_default`` instance attribute
            (which defaults to True).
          timeout(Optional[int]): The max amount of time, in
            milliseconds, to wait on this queue.

        .. versionchanged:: 2.0.0
           The ``fail_fast`` parameter now defaults to ``self.fail_fast_default``
           (which defaults to True).
        """
        try:
            queues = [
                self.queues[queue_name],
                self.queues[dq_name(queue_name)],
            ]
        except KeyError:
            raise QueueNotFound(queue_name) from None

        deadline = timeout and time.monotonic() + timeout / 1000
        should_fail_fast = fail_fast if fail_fast is not None else self.fail_fast_default
        while True:
            for queue in queues:
                join_timeout = deadline and deadline - time.monotonic()
                join_queue(queue, timeout=join_timeout)

            # We cycle through $queue then $queue.DQ then $queue
            # again in case the messages that were on the DQ got
            # moved back on $queue.
            for queue in queues:
                if queue.unfinished_tasks:
                    break
            else:
                if should_fail_fast:
                    for message in self.dead_letters_by_queue[queue_name]:
                        raise (message._exception or Exception("Message failed with unknown error")) from None

                return


class _StubConsumer(Consumer):
    def __init__(self, queue, dead_letters, timeout):
        self.queue = queue
        self.dead_letters = dead_letters
        self.timeout = timeout

    def ack(self, message):
        self.queue.task_done()

    def nack(self, message):
        self.queue.task_done()
        self.dead_letters.append(message)

    def __next__(self):
        try:
            data = self.queue.get(timeout=self.timeout / 1000)
            message = Message.decode(data)
            return _StubMessageProxy(message)
        except Empty:
            return None


class _StubMessageProxy(MessageProxy):
    def clear_exception(self) -> None:
        """Let the GC handle the cycle once the message is no longer
        in use.  This lets us keep showing full stack traces in
        failing tests.  See comment in `Worker' for details.
        """
