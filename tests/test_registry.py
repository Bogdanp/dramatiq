import dramatiq
from dramatiq.registry import Registry


def test_registry_can_be_declared():

    Registry()


def test_actor_can_be_declared_on_registry():
    # When I have a Registry
    reg = Registry()

    # Given that I've decorated a function with @registry.actor
    @reg.actor
    def add(x, y):
        return x + y

    # I expect that function to become an instance of Actor
    assert isinstance(add, dramatiq.Actor)
    assert add.broker is reg
    assert len(reg.actors) == 1
