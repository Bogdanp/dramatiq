import pytest


slow = pytest.mark.skipif(
    not pytest.config.getoption("--with-slow-tests"),
    reason="need --with-slow-tests option to run"
)
