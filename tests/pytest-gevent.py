#!python
try:
    from gevent import monkey; monkey.patch_all()  # noqa
except ImportError:
    import sys

    sys.stderr.write("error: gevent is missing. Run `pip install gevent`.")
    sys.exit(1)

import sys

import pytest

if __name__ == "__main__":
    sys.exit(pytest.main(args=sys.argv[1:]))
