#!python
import sys
import warnings

# Check for free-threaded Python before gevent patching
if hasattr(sys, "_is_gil_enabled") and not sys._is_gil_enabled():  # noqa: SLF001
    warnings.warn(
        "pytest-gevent is running on free-threaded Python (PEP 703). "
        "gevent will re-enable the GIL, which defeats the purpose of "
        "using free-threaded Python. Consider running pytest without "
        "gevent for free-threaded execution.",
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
