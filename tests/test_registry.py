import pytest

import dramatiq
from dramatiq import Middleware, get_broker, set_broker
from dramatiq.brokers.stub import StubBroker
from dramatiq.errors import ActorNotFound
from dramatiq.registry import Registry, disable_registry, enable_registry, get_registry

from .common import worker


@pytest.fixture(autouse=True)
def cleanup_registry():
    yield
    disable_registry()


def test_registry_can_be_declared():
    reg = Registry()
    assert reg.actors == {}
    assert reg.broker is None
    assert reg.get_declared_actors() == set()


def test_actor_can_be_declared_on_registry():
    reg = Registry()

    @reg.actor
    def add(x, y):
        return x + y

    assert isinstance(add, dramatiq.Actor)
    assert "add" in reg.actors
    assert reg.get_actor("add") is add
    assert reg.get_declared_actors() == {"add"}


def test_duplicate_actor_in_registry_raises():
    reg = Registry()

    @reg.actor
    def task():
        pass

    with pytest.raises(ValueError, match="already registered"):
        @reg.actor(actor_name="task")
        def another_task():
            pass


def test_actor_not_found_in_registry():
    reg = Registry()
    with pytest.raises(ActorNotFound):
        reg.get_actor("nonexistent")


def test_registry_bind_broker(stub_broker: StubBroker):
    reg = Registry()

    @reg.actor
    def multiply(x, y):
        return x * y

    reg.bind_broker(stub_broker)

    assert reg.broker is stub_broker
    assert multiply.broker is stub_broker
    assert stub_broker.get_actor("multiply") is multiply


def test_registry_option_validation_on_bind(stub_broker: StubBroker):
    class CustomMiddleware(Middleware):
        @property
        def actor_options(self):
            return {"custom_tag"}

    reg = Registry()

    @reg.actor(custom_tag="production")
    def tagged_task():
        pass

    # Binding to broker without CustomMiddleware should fail validation
    with pytest.raises(ValueError, match="custom_tag"):
        reg.bind_broker(stub_broker)

    # Adding CustomMiddleware to broker should allow successful binding
    stub_broker.add_middleware(CustomMiddleware())
    reg.bind_broker(stub_broker)
    assert reg.broker is stub_broker


def test_enqueue_before_binding_raises():
    reg = Registry()

    @reg.actor
    def standalone():
        pass

    with pytest.raises(RuntimeError, match="registry has not been bound to a broker"):
        standalone.send()


def test_global_registry_mode(stub_broker: StubBroker):
    # Enable global registry mode
    reg = enable_registry()
    assert get_registry() is reg

    # Declare actors with standard @dramatiq.actor without having a broker configured
    @dramatiq.actor
    def greet(name):
        return f"Hello, {name}!"

    assert "greet" in reg.actors
    assert reg.get_actor("greet") is greet

    # Setting the global broker automatically binds the global registry
    set_broker(stub_broker)
    assert reg.broker is stub_broker
    assert stub_broker.get_actor("greet") is greet

    # Messages can now be sent normally
    with worker(stub_broker, worker_threads=1) as stub_worker:
        greet.send("World")
        stub_broker.join(greet.queue_name)
        stub_worker.join()


def test_multiple_modular_registries(stub_broker: StubBroker):
    """Test that multiple registries can be used to partition tasks across distinct queues."""
    billing_registry = Registry()
    email_registry = Registry()

    results = []

    @billing_registry.actor(queue_name="billing")
    def charge(amount):
        results.append(f"charged_{amount}")

    @email_registry.actor(queue_name="email")
    def send_receipt(email):
        results.append(f"emailed_{email}")

    billing_registry.bind_broker(stub_broker)
    email_registry.bind_broker(stub_broker)

    with worker(stub_broker, queues={"billing", "email"}, worker_threads=1) as stub_worker:
        charge.send(100)
        send_receipt.send("user@example.com")
        stub_broker.join("billing")
        stub_broker.join("email")
        stub_worker.join()

    assert set(results) == {"charged_100", "emailed_user@example.com"}
