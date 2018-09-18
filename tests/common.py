import os
import platform
from contextlib import contextmanager

import pytest

from dramatiq import Worker


@contextmanager
def worker(*args, **kwargs):
    try:
        worker = Worker(*args, **kwargs)
        worker.start()
        yield worker
    finally:
        worker.stop()


skip_on_travis = pytest.mark.skipif(os.getenv("TRAVIS") == "1", reason="test skipped on Travis")
skip_on_windows = pytest.mark.skipif(platform.system() == "Windows", reason="test skipped on Windows")
skip_on_pypy = pytest.mark.skipif(platform.python_implementation() == "PyPy", reason="Time limits are not supported under PyPy.")
