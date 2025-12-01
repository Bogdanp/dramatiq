"""Tests for dramatiq's types.

Unlike other test files which are run with pytest,
this test file should be type-checked with mypy,
to test that Dramatiq's types can be "consumed" by user code without type errors.
"""

from __future__ import annotations

from typing import ParamSpec, TypeVar

import dramatiq

P = ParamSpec("P")
R = TypeVar("R")

broker = dramatiq.get_broker()


class ArgType:
    pass


class ReturnType:
    pass


class CustomActor(dramatiq.Actor[P, R]):
    pass


# # # Tests for @actor decorator # # #


@dramatiq.actor
def actor(arg: ArgType) -> ReturnType:
    return ReturnType()


@dramatiq.actor()
def actor_no_options(arg: ArgType) -> ReturnType:
    return ReturnType()


@dramatiq.actor(
    actor_name="actor_with_options",
    queue_name="some_queue",
    priority=2,
    broker=broker,
    max_age=1,
)
def actor_with_options(arg: ArgType) -> ReturnType:
    return ReturnType()


@dramatiq.actor(
    actor_class=CustomActor,
    actor_name="actor_with_custom_actor_class",
    queue_name="some_queue",
    priority=2,
    broker=broker,
    max_age=1,
)
def actor_with_custom_actor_class(arg: ArgType) -> ReturnType:
    return ReturnType()


@dramatiq.actor
async def async_actor(arg: ArgType) -> ReturnType:
    return ReturnType()


@dramatiq.actor()
async def async_actor_no_options(arg: ArgType) -> ReturnType:
    return ReturnType()


@dramatiq.actor(
    actor_name="async_actor_with_options",
    queue_name="some_queue",
    priority=2,
    broker=broker,
    max_age=1,
)
async def async_actor_with_options(arg: ArgType) -> ReturnType:
    return ReturnType()


@dramatiq.actor(
    actor_class=CustomActor,
    actor_name="async_actor_with_custom_actor_class",
    queue_name="some_queue",
    priority=2,
    broker=broker,
    max_age=1,
)
async def async_actor_with_custom_actor_class(arg: ArgType) -> ReturnType:
    return ReturnType()
