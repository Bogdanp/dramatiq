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
from queue import Empty
from random import uniform
from time import time
from typing import TYPE_CHECKING, Iterator, Tuple

from .errors import QueueJoinTimeout

if TYPE_CHECKING:
    from .queues import Queue


def compute_backoff(attempts: int, *, factor: int = 5, jitter: bool = True, max_backoff: int = 2000, max_exponent: int = 32) -> Tuple[int, float]:  # noqa: B950
    """Compute an exponential backoff value based on some number of attempts.

    Parameters:
      attempts(int): The number of attempts there have been so far.
      factor(int): The number of milliseconds to multiply each backoff by.
      max_backoff(int): The max number of milliseconds to backoff by.
      max_exponent(int): The maximum backoff exponent.

    Returns:
      tuple: The new number of attempts and the backoff in milliseconds.
    """
    exponent = min(attempts, max_exponent)
    backoff = min(factor * 2 ** exponent, max_backoff)
    if jitter:
        backoff /= 2
        backoff = int(backoff + uniform(0, backoff))
    return attempts + 1, backoff


def current_millis() -> int:
    """Returns the current UNIX time in milliseconds.
    """
    return int(time() * 1000)


def iter_queue(queue: "Queue") -> Iterator:
    """Iterate over the messages on a queue until it's empty.  Does
    not block while waiting for messages.

    Parameters:
      queue(Queue): The queue to iterate over.

    Returns:
      generator[object]: The iterator.
    """
    while True:
        try:
            yield queue.get_nowait()
        except Empty:
            break


def join_queue(queue: "Queue", timeout: float = None) -> None:
    """The join() method of standard queues in Python doesn't support
    timeouts.  This implements the same functionality as that method,
    with optional timeout support, by depending the internals of
    Queue.

    Raises:
      QueueJoinTimeout: When the timeout is reached.

    Parameters:
      timeout(Optional[float])
    """
    with queue.all_tasks_done:
        while queue.unfinished_tasks:
            finished_in_time = queue.all_tasks_done.wait(timeout=timeout)
            if not finished_in_time:
                raise QueueJoinTimeout("timed out after %.02f seconds" % timeout)


def join_all(joinables, timeout: int) -> None:
    """Wait on a list of objects that can be joined with a total
    timeout represented by ``timeout``.

    Parameters:
      joinables(object): Objects with a join method.
      timeout(int): The total timeout in milliseconds.
    """
    started, elapsed = current_millis(), 0
    for ob in joinables:
        ob.join(timeout=timeout / 1000)
        elapsed = current_millis() - started
        timeout = max(0, timeout - elapsed)


def q_name(queue_name: str) -> str:
    """Returns the canonical queue name for a given queue.
    """
    if queue_name.endswith(".DQ") or queue_name.endswith(".XQ"):
        return queue_name[:-3]
    return queue_name


def dq_name(queue_name: str) -> str:
    """Returns the delayed queue name for a given queue.  If the given
    queue name already belongs to a delayed queue, then it is returned
    unchanged.
    """
    if queue_name.endswith(".DQ"):
        return queue_name

    if queue_name.endswith(".XQ"):
        queue_name = queue_name[:-3]
    return queue_name + ".DQ"


def xq_name(queue_name: str) -> str:
    """Returns the dead letter queue name for a given queue.  If the
    given queue name belongs to a delayed queue, the dead letter queue
    name for the original queue is generated.
    """
    if queue_name.endswith(".XQ"):
        return queue_name

    if queue_name.endswith(".DQ"):
        queue_name = queue_name[:-3]
    return queue_name + ".XQ"
