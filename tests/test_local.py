import pytest

import remoulade
from remoulade import group
from remoulade.results import Results
from remoulade.results.backends import LocalBackend


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_local_broker_cannot_have_non_local_backend(local_broker, backend, result_backends):
    # Given a backend
    result_backend = result_backends[backend]

    # Which is not a LocalBackend
    assert not isinstance(backend, LocalBackend)

    # Cannot be used with LocalBroker
    with pytest.raises(RuntimeError):
        local_broker.add_middleware(Results(backend=result_backend))


def test_local_broker_get_result_in_message(local_broker):
    # Given that I have an actor that stores its results
    @remoulade.actor(store_results=True)
    def do_work():
        return 1

    # And this actor is declared
    local_broker.declare_actor(do_work)

    # When I send that actor a message
    message = do_work.send()

    # I should get the right result
    assert message.result.get() == 1


def test_local_broker_with_pipes(local_broker):
    # Given that I have an actor that stores its results
    @remoulade.actor(store_results=True)
    def add(a, b):
        return a + b

    # And this actor is declared
    local_broker.declare_actor(add)

    # When I run a pipe
    pipe = add.message(1, 2) | add.message(3)
    pipe.run()

    # I should get the right result
    assert pipe.result.get() == 6


def test_local_broker_with_groups(local_broker):
    # Given that I have an actor that stores its results
    @remoulade.actor(store_results=True)
    def add(a, b):
        return a + b

    # And this actor is declared
    local_broker.declare_actor(add)

    # When I run a group
    g = group([add.message(1, 2), add.message(3, 4), add.message(4, 5)])
    g.run()

    assert list(g.results.get()) == [3, 7, 9]
