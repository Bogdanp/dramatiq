from __future__ import annotations

import pytest

import dramatiq
from dramatiq import Message


def test_registry_collects_actors_before_binding(stub_broker):
    registry = dramatiq.Registry()

    @registry.actor
    def add(x, y):
        return x + y

    assert registry.get_declared_actors() == {"add"}
    assert stub_broker.get_declared_actors() == set()

    registry.bind(stub_broker)

    assert stub_broker.get_actor("add") is add
    assert add.broker is stub_broker


def test_registry_can_bind_to_the_global_broker(stub_broker):
    registry = dramatiq.Registry()

    @registry.actor
    def add(x, y):
        return x + y

    registry.bind()

    assert stub_broker.get_actor("add") is add


def test_registry_defers_actor_option_validation_until_binding(stub_broker):
    registry = dramatiq.Registry()

    @registry.actor(invalid_option=32)
    def add(x, y):
        return x + y

    assert registry.get_declared_actors() == {"add"}
    assert stub_broker.get_declared_actors() == set()

    with pytest.raises(ValueError) as exc_info:
        registry.bind(stub_broker)

    assert str(exc_info.value) == (
        "The following actor options are undefined: invalid_option. "
        "Did you forget to add a middleware to your Broker?"
    )
    assert stub_broker.get_declared_actors() == set()


def test_registry_validates_actor_options_when_binding(stub_broker):
    registry = dramatiq.Registry()

    @registry.actor(max_retries=32)
    def add(x, y):
        return x + y

    registry.bind(stub_broker)

    assert add.options["max_retries"] == 32


def test_registry_actors_can_be_sent_after_binding(stub_broker):
    registry = dramatiq.Registry()

    @registry.actor
    def add(x, y):
        return x + y

    registry.bind(stub_broker)

    enqueued_message = add.send(1, 2)
    enqueued_message_data = stub_broker.queues["default"].get(timeout=1)
    assert enqueued_message == Message.decode(enqueued_message_data)


def test_registry_actors_cannot_be_sent_before_binding():
    registry = dramatiq.Registry()

    @registry.actor
    def add(x, y):
        return x + y

    with pytest.raises(RuntimeError, match="bound to a Broker"):
        add.send(1, 2)


def test_registry_rejects_duplicate_actor_names():
    registry = dramatiq.Registry()

    @registry.actor(actor_name="foo")
    def add(x, y):
        return x + y

    with pytest.raises(ValueError) as exc_info:

        @registry.actor(actor_name="foo")
        def subtract(x, y):
            return x - y

    assert str(exc_info.value) == "An actor named 'foo' is already registered."


def test_registry_rejects_broker_actor_name_collisions(stub_broker):
    registry = dramatiq.Registry()

    @dramatiq.actor(actor_name="foo")
    def add(x, y):
        return x + y

    @registry.actor(actor_name="foo")
    def subtract(x, y):
        return x - y

    with pytest.raises(ValueError) as exc_info:
        registry.bind(stub_broker)

    assert str(exc_info.value) == "An actor named 'foo' is already registered."
    assert stub_broker.get_actor("foo") is add


def test_registry_fails_given_invalid_queue_names():
    registry = dramatiq.Registry()

    with pytest.raises(ValueError):

        @registry.actor(queue_name="$2@!@#")
        def add(x, y):
            return x + y
