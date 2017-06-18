from time import time


def current_millis():
    "Returns the current UNIX time in milliseconds."
    return int(time() * 1000)
