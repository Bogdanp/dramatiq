from __future__ import annotations

import pytest

from dramatiq.common import dq_name, q_name, xq_name


@pytest.mark.parametrize(
    "given,expected",
    [
        ("default", "default"),
        ("default.DQ", "default"),
        ("default.XQ", "default"),
    ],
)
def test_q_name_returns_canonical_names(given, expected):
    assert q_name(given) == expected


@pytest.mark.parametrize(
    "given,expected",
    [
        ("default", "default.DQ"),
        ("default.DQ", "default.DQ"),
        ("default.XQ", "default.DQ"),
    ],
)
def test_dq_name_returns_canonical_delay_names(given, expected):
    assert dq_name(given) == expected


@pytest.mark.parametrize(
    "given,expected",
    [
        ("default", "default.XQ"),
        ("default.DQ", "default.XQ"),
        ("default.XQ", "default.XQ"),
    ],
)
def test_xq_name_returns_delay_names(given, expected):
    assert xq_name(given) == expected
