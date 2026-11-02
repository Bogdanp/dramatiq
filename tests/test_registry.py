from __future__ import annotations

import pytest

import dramatiq
from dramatiq.brokers.stub import StubBroker
from dramatiq.errors import ActorNotFound


def test_registry_can_declare_and_bind_actors():
    registry = dramatiq.Registry()

    @registry.actor(max_retries=5, queue_name="custom")
    def add(x, y):
        return x + y

    assert add(2, 3) == 5
    assert registry.get_declared_actors() == {"add"}
    assert registry.get_actor("add") is add

    # Sending before binding a broker raises RuntimeError
    with pytest.raises(RuntimeError, match="not bound to a broker"):
        add.send(2, 3)

    broker = StubBroker()
    registry.bind_broker(broker)

    assert add.broker is broker
    assert broker.get_actor("add") is add
    assert "custom" in broker.get_declared_queues()

    msg = add.send(2, 3)
    assert msg.actor_name == "add"
    assert msg.queue_name == "custom"


def test_registry_validates_invalid_options_on_bind():
    registry = dramatiq.Registry()

    @registry.actor(nonexistent_option=True)
    def bad_actor():
        pass

    broker = StubBroker()
    with pytest.raises(ValueError, match="The following actor options are undefined: nonexistent_option"):
        registry.bind_broker(broker)

    # Actor should not be registered on broker if validation failed
    assert "bad_actor" not in broker.get_declared_actors()


def test_registry_rejects_duplicate_actor_names():
    registry = dramatiq.Registry()

    @registry.actor(actor_name="dup")
    def first():
        pass

    with pytest.raises(ValueError, match="An actor named 'dup' is already registered"):

        @registry.actor(actor_name="dup")
        def second():
            pass


def test_registry_lookup_missing_actor_raises_actor_not_found():
    registry = dramatiq.Registry()
    with pytest.raises(ActorNotFound):
        registry.get_actor("unknown")


def test_enable_registry_global_mode_and_set_broker():
    dramatiq.broker.global_broker = None
    registry = dramatiq.enable_registry()
    try:
        @dramatiq.actor(max_retries=3)
        def multiply(x, y):
            return x * y

        # Global broker was not auto-instantiated
        assert dramatiq.broker.global_broker is None
        assert registry.get_actor("multiply") is multiply

        broker = StubBroker()
        dramatiq.set_broker(broker)

        assert multiply.broker is broker
        assert broker.get_actor("multiply") is multiply
    finally:
        dramatiq.disable_registry()


def test_generic_actor_with_registry():
    registry = dramatiq.Registry()

    class MultiplyTask(dramatiq.GenericActor):
        class Meta:
            actor = registry.actor
            queue_name = "math"

        def perform(self, x, y):
            return x * y

    assert MultiplyTask(3, 4) == 12
    assert registry.get_actor("MultiplyTask") is MultiplyTask.__actor__

    broker = StubBroker()
    registry.transfer_actors(broker)
    assert broker.get_actor("MultiplyTask") is MultiplyTask.__actor__
