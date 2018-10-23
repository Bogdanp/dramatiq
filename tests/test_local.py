import pytest

import dramatiq
from dramatiq import group
from dramatiq.results import Results
from dramatiq.results.backends import LocalBackend


@pytest.mark.parametrize("backend", ["memcached", "redis", "stub"])
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
    @dramatiq.actor(store_results=True)
    def do_work():
        return 1

    # When I send that actor a message
    message = do_work.send()

    # I should get the right result
    assert message.get_result() == 1


def test_local_broker_with_pipes(local_broker):
    # Given that I have an actor that stores its results
    @dramatiq.actor(store_results=True)
    def add(a, b):
        return a + b

    # When I run a pipe
    pipe = add.message(1, 2) | add.message(3)
    pipe.run()

    # I should get the right result
    assert pipe.get_result() == 6


def test_local_broker_with_groups(local_broker):
    # Given that I have an actor that stores its results
    @dramatiq.actor(store_results=True)
    def add(a, b):
        return a + b

    # When I run a group
    g = group([add.message(1, 2), add.message(3, 4), add.message(4, 5)])
    g.run()

    assert list(g.get_results()) == [3, 7, 9]
