from queue import Empty
from random import uniform
from time import time


def compute_backoff(attempts, *, factor=5, jitter=True, max_backoff=2000, max_exponent=32):
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


def current_millis():
    "Returns the current UNIX time in milliseconds."
    return int(time() * 1000)


def iter_queue(queue):
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


def join_all(joinables, timeout):
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


def q_name(queue_name):
    """Returns the canonical queue name for a given queue.
    """
    if queue_name.endswith(".DQ") or queue_name.endswith(".XQ"):
        return queue_name[:-3]
    return queue_name


def dq_name(queue_name):
    """Returns the delayed queue name for a given queue.  If the given
    queue name already belongs to a delayed queue, then it is returned
    unchanged.
    """
    if queue_name.endswith(".DQ"):
        return queue_name

    if queue_name.endswith(".XQ"):
        queue_name = queue_name[:-3]
    return f"{queue_name}.DQ"


def xq_name(queue_name):
    """Returns the dead letter queue name for a given queue.  If the
    given queue name belongs to a delayed queue, the dead letter queue
    name for the original queue is generated.
    """
    if queue_name.endswith(".XQ"):
        return queue_name

    if queue_name.endswith(".DQ"):
        queue_name = queue_name[:-3]
    return f"{queue_name}.XQ"
