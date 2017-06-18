from time import time


def current_millis():
    "Returns the current UNIX time in milliseconds."
    return int(time() * 1000)


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
