from __future__ import annotations

import logging

import pytest

import dramatiq
import dramatiq.broker
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from dramatiq.middleware import Middleware

from .common import RABBITMQ_CREDENTIALS, skip_on_windows


class EmptyMiddleware(Middleware):
    pass


def test_broker_uses_rabbitmq_if_not_set():
    # Given that no global broker is set
    dramatiq.broker.global_broker = None

    # If I try to get the global broker
    broker = dramatiq.get_broker()

    # I expect it to be a RabbitmqBroker instance
    assert isinstance(broker, RabbitmqBroker)


@skip_on_windows
def test_broker_middleware_can_be_added_before_other_middleware(stub_broker):
    from dramatiq.middleware import AgeLimit

    # Given that I have a custom middleware
    empty_middleware = EmptyMiddleware()

    # If I add it before the AgeLimit middleware
    stub_broker.add_middleware(empty_middleware, before=AgeLimit)

    # I expect it to be the first middleware
    assert stub_broker.middleware[0] == empty_middleware


@skip_on_windows
def test_broker_middleware_can_be_added_after_other_middleware(stub_broker):
    from dramatiq.middleware import AgeLimit

    # Given that I have a custom middleware
    empty_middleware = EmptyMiddleware()

    # If I add it after the AgeLimit middleware
    stub_broker.add_middleware(empty_middleware, after=AgeLimit)

    # I expect it to be the second middleware
    assert stub_broker.middleware[1] == empty_middleware


def test_broker_middleware_can_fail_to_be_added_before_or_after_missing_middleware(stub_broker):
    # Given that I have a custom middleware
    empty_middleware = EmptyMiddleware()

    # If I add it after a middleware that isn't registered
    # I expect a ValueError to be raised
    with pytest.raises(ValueError):
        stub_broker.add_middleware(empty_middleware, after=EmptyMiddleware)


@skip_on_windows
def test_broker_middleware_cannot_be_addwed_both_before_and_after(stub_broker):
    from dramatiq.middleware import AgeLimit

    # Given that I have a custom middleware
    empty_middleware = EmptyMiddleware()

    # If I add it with both before and after parameters
    # I expect an AssertionError to be raised
    with pytest.raises(AssertionError):
        stub_broker.add_middleware(empty_middleware, before=AgeLimit, after=AgeLimit)


def test_can_instantiate_brokers_without_middleware():
    # Given that I have an empty list of middleware
    # When I pass that to the RMQ Broker
    broker = RabbitmqBroker(middleware=[], credentials=RABBITMQ_CREDENTIALS)

    # Then I should get back a broker with no middleware
    assert not broker.middleware


def test_broker_middleware_logs_warning_when_added_twice(stub_broker, caplog):
    # Set the log level to capture warnings
    caplog.set_level(logging.WARNING)

    # Given that I have a custom middleware
    empty_middleware1 = EmptyMiddleware()
    empty_middleware2 = EmptyMiddleware()

    # When I add the first middleware
    stub_broker.add_middleware(empty_middleware1)

    # And I add another middleware of the same type
    stub_broker.add_middleware(empty_middleware2)

    # Then I expect a warning to be logged
    assert any(
        "You're adding a middleware of the same type twice" in record.message
        for record in caplog.records
        if record.levelname == "WARNING"
    )

    # And I expect both middlewares to be added
    assert empty_middleware1 in stub_broker.middleware
    assert empty_middleware2 in stub_broker.middleware
