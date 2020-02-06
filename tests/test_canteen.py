import multiprocessing

import pytest

from dramatiq.canteen import Canteen, canteen_add, canteen_get, canteen_try_init


def test_canteen_add_adds_paths():
    # Given that I have a Canteen
    c = multiprocessing.Value(Canteen)

    # When I append a couple of paths and mark it ready
    with canteen_try_init(c):
        canteen_add(c, "hello")
        canteen_add(c, "there")

    # Then those paths should be stored in the canteen
    assert canteen_get(c) == ["hello", "there"]


def test_canteen_add_fails_when_adding_too_many_paths():
    # Given that I have a Canteen
    c = Canteen()

    # When I append too many paths
    # Then a RuntimeError should be raised
    with pytest.raises(RuntimeError):
        for _ in range(1024):
            canteen_add(c, "0" * 1024)


def test_canteen_try_init_runs_at_most_once():
    # Given that I have a Canteen
    c = multiprocessing.Value(Canteen)

    # When I run two canteen_try_init blocks
    with canteen_try_init(c) as acquired:
        if acquired:
            canteen_add(c, "hello")

    with canteen_try_init(c) as acquired:
        if acquired:
            canteen_add(c, "goodbye")

    # Then only the first one should run
    assert canteen_get(c) == ["hello"]
