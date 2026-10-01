import pytest
import dramatiq
from dramatiq import Registry, enable_registry, disable_registry, get_registry, transfer_actors


@pytest.fixture
def clean_registry():
    disable_registry()
    yield
    disable_registry()


def test_registry_can_declare_actors_without_broker():
    # Given a fresh registry
    registry = Registry()

    # When we declare actors on the registry
    @registry.actor
    def add(x, y):
        return x + y

    @registry.actor(actor_name="custom_multiply", queue_name="math", priority=10)
    def multiply(x, y):
        return x * y

    # Then the actors are registered in the registry without any broker
    assert "add" in registry
    assert "custom_multiply" in registry
    assert len(registry) == 2
    assert add.broker is None
    assert multiply.broker is None
    assert multiply.queue_name == "math"
    assert multiply.priority == 10

    # And they can still be called synchronously
    assert add(2, 3) == 5
    assert multiply(3, 4) == 12


def test_registry_actor_cannot_send_before_binding():
    registry = Registry()

    @registry.actor
    def do_work():
        return 42

    with pytest.raises(RuntimeError, match="not bound to a broker"):
        do_work.send()


def test_registry_bind_transfers_actors_to_broker(stub_broker, stub_worker):
    registry = Registry()
    results = []

    @registry.actor
    def compute(x):
        results.append(x * 2)

    # Before binding, broker does not know about the actor
    assert "compute" not in stub_broker.actors

    # When the registry is bound to the broker
    registry.bind(stub_broker)

    # Then the actor has the broker and is declared on the broker
    assert compute.broker is stub_broker
    assert "compute" in stub_broker.actors

    # And messages can be sent and executed
    compute.send(21)
    stub_broker.join(compute.queue_name)
    stub_worker.join()

    assert results == [42]


def test_registry_rejects_duplicate_names():
    registry = Registry()

    @registry.actor
    def task_one():
        pass

    with pytest.raises(ValueError, match="already registered in this registry"):
        @registry.actor(actor_name="task_one")
        def task_two():
            pass


def test_transfer_actors_helper(stub_broker):
    reg1 = Registry()
    reg2 = Registry()

    @reg1.actor
    def task_a():
        pass

    @reg2.actor
    def task_b():
        pass

    transfer_actors(stub_broker, [reg1, reg2])

    assert "task_a" in stub_broker.actors
    assert "task_b" in stub_broker.actors
    assert task_a.broker is stub_broker
    assert task_b.broker is stub_broker


def test_global_registry_mode(clean_registry, stub_broker, stub_worker):
    # When global registry mode is enabled
    reg = enable_registry()
    assert get_registry() is reg

    results = []

    # Standard @dramatiq.actor decorator registers with global registry without needing broker
    @dramatiq.actor
    def global_task(val):
        results.append(val + 1)

    assert "global_task" in reg
    assert global_task.broker is None

    # When binding registry to stub broker
    reg.bind(stub_broker)
    assert global_task.broker is stub_broker
    assert "global_task" in stub_broker.actors

    # Messages can be processed
    global_task.send(99)
    stub_broker.join(global_task.queue_name)
    stub_worker.join()

    assert results == [100]


def test_registry_iteration_and_indexing():
    registry = Registry()

    @registry.actor
    def first():
        pass

    @registry.actor
    def second():
        pass

    actor_names = [a.actor_name for a in registry]
    assert sorted(actor_names) == ["first", "second"]
    assert registry["first"].actor_name == "first"
    assert registry["second"].actor_name == "second"
