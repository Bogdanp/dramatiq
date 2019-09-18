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
    from dramatiq.middleware import Prometheus

    # Given that I have a custom middleware
    empty_middleware = EmptyMiddleware()

    # If I add it before the Prometheus middleware
    stub_broker.add_middleware(empty_middleware, before=Prometheus)

    # I expect it to be the first middleware
    assert stub_broker.middleware[0] == empty_middleware


@skip_on_windows
def test_broker_middleware_can_be_added_after_other_middleware(stub_broker):
    from dramatiq.middleware import Prometheus

    # Given that I have a custom middleware
    empty_middleware = EmptyMiddleware()

    # If I add it after the Prometheus middleware
    stub_broker.add_middleware(empty_middleware, after=Prometheus)

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
    from dramatiq.middleware import Prometheus

    # Given that I have a custom middleware
    empty_middleware = EmptyMiddleware()

    # If I add it with both before and after parameters
    # I expect an AssertionError to be raised
    with pytest.raises(AssertionError):
        stub_broker.add_middleware(empty_middleware, before=Prometheus, after=Prometheus)


def test_can_instantiate_brokers_without_middleware():
    # Given that I have an empty list of middleware
    # When I pass that to the RMQ Broker
    broker = RabbitmqBroker(middleware=[], credentials=RABBITMQ_CREDENTIALS)

    # Then I should get back a broker with no middleware
    assert not broker.middleware
