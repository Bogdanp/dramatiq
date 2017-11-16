import dramatiq
import pytest


def test_generic_actors_can_be_defined(stub_broker):
    # Given that I've subclassed GenericActor
    class Add(dramatiq.GenericActor):
        def perform(self, x, y):
            return x + y

    # Then Add should be an instance of Actor
    assert isinstance(Add, dramatiq.Actor)

    # And it should be callable
    assert Add(1, 2) == 3


def test_generic_actors_can_be_assigned_options(stub_broker):
    # Given that I've subclassed GenericActor
    class Add(dramatiq.GenericActor):
        # When I set its max_retries value to 32
        class Meta:
            max_retries = 32

        def perform(self, x, y):
            return x + y

    # Then the resulting actor should have that option set
    assert Add.options["max_retries"] == 32


def test_generic_actors_raise_not_implemented_if_perform_is_missing(stub_broker):
    # Given that I've subclassed GenericActor without implementing perform
    class Foo(dramatiq.GenericActor):
        pass

    # When I call that actor
    # Then a NotImplementedError should be raised
    with pytest.raises(NotImplementedError):
        Foo()


def test_generic_actors_can_be_abstract(stub_broker, stub_worker):
    # Given that I have a calls database
    calls = set()

    # And I've subclassed GenericActor
    class BaseTask(dramatiq.GenericActor):
        # When I set abstract to True
        class Meta:
            abstract = True
            queue_name = "tasks"

        def get_task_name(self):
            raise NotImplementedError

        def perform(self):
            calls.add(self.get_task_name())

    # Then BaseTask should not be an Actor
    assert not isinstance(BaseTask, dramatiq.Actor)

    # When I subclass BaseTask
    class FooTask(BaseTask):
        def get_task_name(self):
            return "Foo"

    class BarTask(BaseTask):
        def get_task_name(self):
            return "Bar"

    # Then both subclasses should be actors
    # And they should inherit the parent's meta
    assert isinstance(FooTask, dramatiq.Actor)
    assert isinstance(BarTask, dramatiq.Actor)
    assert FooTask.queue_name == BarTask.queue_name == "tasks"

    # When I send both actors a message
    # And wait for them to get processed
    FooTask.send()
    BarTask.send()
    stub_broker.join(queue_name=BaseTask.Meta.queue_name)
    stub_worker.join()

    # Then my calls database should contain both task names
    assert calls == {"Foo", "Bar"}
