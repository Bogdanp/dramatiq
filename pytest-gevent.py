#!python
import sys
import warnings

# Check for a free-threaded Python build (PEP 703) before gevent patching.
#
# Note: a free-threaded build may already have the GIL enabled at this point
# (e.g. via early imports), so we base this on the build rather than
# the current GIL state.
# See https://docs.python.org/3/howto/free-threading-python.html#identifying-free-threaded-python
if "free-threading" in sys.version:
    warnings.warn(
        "pytest-gevent is running on a free-threaded Python build (PEP 703). "
        "gevent requires the GIL, which defeats the purpose of using "
        "free-threaded Python. Consider running pytest without gevent.",
        category=RuntimeWarning,
    )

try:
    from gevent import monkey

    monkey.patch_all()
except ImportError:
    sys.stderr.write("error: gevent is missing. Run `pip install gevent`.")
    sys.exit(1)

import pytest

if __name__ == "__main__":
    sys.exit(pytest.main(args=sys.argv[1:]))
