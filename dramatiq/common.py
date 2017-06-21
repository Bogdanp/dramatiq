from queue import Empty
from time import time


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


def dq_name(queue_name):
    """Returns the delayed queue name for a given queue.
    """
    return f"{queue_name}.DQ"


def xq_name(queue_name):
    """Returns the dead letter queue name for a given queue.
    """
    return f"{queue_name}.XQ"
