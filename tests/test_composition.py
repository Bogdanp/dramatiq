import time
from threading import Condition

import pytest

import remoulade
from remoulade import group, pipeline, CollectionResults
from remoulade.results import Results, ResultTimeout, ErrorStored, ResultMissing
from remoulade.errors import ResultNotStored


def test_messages_can_be_piped(stub_broker):
    # Given an actor that adds two numbers together
    @remoulade.actor
    def add(x, y):
        return x + y

    # And this actor is declared
    stub_broker.declare_actor(add)

    # When I pipe some messages intended for that actor together
    pipe = add.message(1, 2) | add.message(3) | add.message(4)

    # Then I should get back a pipeline object
    assert isinstance(pipe, pipeline)

    def filter_options(message):
        return {key: value for (key, value) in message.items() if key != 'options'}

    # If I build a pipeline
    first_target = pipe.build()
    # And each message in the pipeline should reference the next message in line
    assert filter_options(first_target.options["pipe_target"]) == filter_options(pipe.children[1].asdict())
    second_target = first_target.options["pipe_target"]
    assert filter_options(second_target["options"]["pipe_target"]) == filter_options(pipe.children[2].asdict())
    third_target = second_target["options"]["pipe_target"]
    assert "pipe_target" not in third_target["options"]


def test_pipelines_flatten_child_pipelines(stub_broker):
    # Given an actor that adds two numbers together
    @remoulade.actor
    def add(x, y):
        return x + y

    # And this actor is declared
    stub_broker.declare_actor(add)

    # When I pipe a message intended for that actor and another pipeline together
    pipe = pipeline([add.message(1, 2), add.message(3) | add.message(4), add.message(5)])

    # Then the inner pipeline should be flattened into the outer pipeline
    assert len(pipe) == 4
    assert pipe.children[0].args == (1, 2)
    assert pipe.children[1].args == (3,)
    assert pipe.children[2].args == (4,)
    assert pipe.children[3].args == (5,)


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_pipe_ignore_message_options(stub_broker, stub_worker, backend, result_backends):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that return something
    @remoulade.actor(store_results=True)
    def do_nothing():
        return 0

    # Nothing should be sent to pipe ignored
    @remoulade.actor(store_results=True)
    def pipe_ignored(*args):
        assert len(args) == 0
        return 1

    # And these actors are declared
    stub_broker.declare_actor(do_nothing)
    stub_broker.declare_actor(pipe_ignored)

    pipe = do_nothing.message() | pipe_ignored.message_with_options(pipe_ignore=True)
    pipe.run()

    assert pipe.result.get(block=True) == 1


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_pipe_ignore_actor_options(stub_broker, stub_worker, backend, result_backends):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that return something
    @remoulade.actor(store_results=True)
    def do_nothing():
        return 0

    # Nothing should be sent to pipe ignored
    @remoulade.actor(store_results=True, pipe_ignore=True)
    def pipe_ignored(*args):
        assert len(args) == 0
        return 1

    # And these actors are declared
    stub_broker.declare_actor(do_nothing)
    stub_broker.declare_actor(pipe_ignored)

    pipe = do_nothing.message() | pipe_ignored.message()
    pipe.run()

    assert pipe.result.get(block=True) == 1


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_pipeline_cannot_have_actor_without_store_results(stub_broker, stub_worker, backend, result_backends):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that return something
    @remoulade.actor()
    def do_nothing():
        return 0

    # Nothing should be sent to pipe ignored
    @remoulade.actor(store_results=True, pipe_ignore=True)
    def pipe_ignored(*args):
        assert len(args) == 0
        return 1

    # And these actors are declared
    stub_broker.declare_actor(do_nothing)
    stub_broker.declare_actor(pipe_ignored)

    pipe = do_nothing.message() | pipe_ignored.message()

    with pytest.raises(ResultNotStored):
        pipe.results


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_pipeline_results_can_be_retrieved(stub_broker, stub_worker, backend, result_backends):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that adds two numbers together and stores the result
    @remoulade.actor(store_results=True)
    def add(x, y):
        return x + y

    # And this actor is declared
    stub_broker.declare_actor(add)

    # When I pipe some messages intended for that actor together and run the pipeline
    pipe = add.message(1, 2) | (add.message(3) | add.message(4))
    pipe.run()

    # Then the pipeline result should be the sum of 1, 2, 3 and 4
    assert pipe.result.get(block=True) == 10

    # And I should be able to retrieve individual results
    assert list(pipe.results.get()) == [3, 6, 10]


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_pipeline_results_respect_timeouts(stub_broker, stub_worker, backend, result_backends):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that waits some amount of time then doubles that amount
    @remoulade.actor(store_results=True)
    def wait(n):
        time.sleep(n)
        return n * 2

    # And this actor is declared
    stub_broker.declare_actor(wait)

    # When I pipe some messages intended for that actor together and run the pipeline
    pipe = wait.message(1) | wait.message() | wait.message()
    pipe.run()

    # And get the results with a lower timeout than the tasks can complete in
    # Then a ResultTimeout error should be raised
    with pytest.raises(ResultTimeout):
        for _ in pipe.results.get(block=True, timeout=1000):
            pass


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_pipelines_expose_completion_stats(stub_broker, stub_worker, backend, result_backends):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that waits some amount of time
    condition = Condition()

    @remoulade.actor(store_results=True)
    def wait(n):
        time.sleep(n)
        with condition:
            condition.notify_all()
            return n

    # And this actor is declared
    stub_broker.declare_actor(wait)

    # When I pipe some messages intended for that actor together and run the pipeline
    pipe = wait.message(1) | wait.message()
    pipe.run()

    # Then every time a job in the pipeline completes, the completed_count should increase
    for count in range(1, len(pipe) + 1):
        with condition:
            condition.wait(2)
            time.sleep(0.1)  # give the worker time to set the result
            assert pipe.results.completed_count == count

    # Finally, completed should be true
    assert pipe.results.completed


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_pipelines_can_be_incomplete(stub_broker, backend, result_backends):
    # Given that I am not running a worker
    # And I have a result backend
    backend = result_backends[backend]
    stub_broker.add_middleware(Results(backend=backend))

    # And I have an actor that does nothing
    @remoulade.actor(store_results=True)
    def do_nothing():
        return None

    # And this actor is declared
    stub_broker.declare_actor(do_nothing)

    # And I've run a pipeline
    pipe = do_nothing.message() | do_nothing.message_with_options(pipe_ignore=True)
    pipe.run()

    # When I check if the pipeline has completed
    # Then it should return False
    assert not pipe.results.completed


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_pipelines_store_results_error(stub_broker, backend, result_backends, stub_worker):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # Given an actor that stores results and fail
    @remoulade.actor(store_results=True)
    def do_work_fail():
        raise ValueError()

    # Given an actor that stores results
    @remoulade.actor(store_results=True)
    def do_work():
        return 42

    # And these actors are declared
    stub_broker.declare_actor(do_work_fail)
    stub_broker.declare_actor(do_work)

    # And I've run a pipeline
    pipe = do_work_fail.message() | do_work.message() | do_work.message()
    pipe.run()

    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    # I get an error
    with pytest.raises(ErrorStored) as e:
        pipe.children[0].result.get(block=True)
    assert str(e.value) == 'ValueError()'

    for i in [1, 2]:
        with pytest.raises(ErrorStored) as e:
            pipe.children[i].result.get(block=True)
        assert str(e.value).startswith('ParentFailed')


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_groups_execute_jobs_in_parallel(stub_broker, stub_worker, backend, result_backends):
    # Given that I have a result backend
    backend = result_backends[backend]
    stub_broker.add_middleware(Results(backend=backend))

    # And I have an actor that sleeps for 100ms
    @remoulade.actor(store_results=True)
    def wait():
        time.sleep(0.1)

    # And this actor is declared
    stub_broker.declare_actor(wait)

    # When I group multiple of these actors together and run them
    t = time.monotonic()
    g = group([wait.message() for _ in range(5)])
    g.run()

    # And wait on the group to complete
    results = list(g.results.get(block=True))

    # Then the total elapsed time should be less than 500ms
    assert time.monotonic() - t <= 0.5

    # And I should get back as many results as there were jobs in the group
    assert len(results) == len(g)

    # And the group should be completed
    assert g.results.completed
    assert isinstance(g.results, CollectionResults)


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_inner_groups_forbidden(stub_broker, stub_worker, backend, result_backends):
    # Given that I have a result backend
    backend = result_backends[backend]
    stub_broker.add_middleware(Results(backend=backend))

    # And I have an actor
    @remoulade.actor()
    def do_work():
        return 1
    # And this actor is declared
    stub_broker.declare_actor(do_work)

    # groups of groups are forbidden
    with pytest.raises(ValueError):
        group(group(do_work.message() for _ in range(2)) for _ in range(3))


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_groups_can_time_out(stub_broker, stub_worker, backend, result_backends):
    # Given that I have a result backend
    backend = result_backends[backend]
    stub_broker.add_middleware(Results(backend=backend))

    # And I have an actor that sleeps for 300ms
    @remoulade.actor(store_results=True)
    def wait():
        time.sleep(0.3)

    # And this actor is declared
    stub_broker.declare_actor(wait)

    # When I group a few jobs together and run it
    g = group(wait.message() for _ in range(2))
    g.run()

    # And wait for the group to complete with a timeout
    # Then a ResultTimeout error should be raised
    with pytest.raises(ResultTimeout):
        g.results.wait(timeout=100)

    # And the group should not be completed
    assert not g.results.completed


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_groups_expose_completion_stats(stub_broker, stub_worker, backend, result_backends):
    # Given that I have a result backend
    backend = result_backends[backend]
    stub_broker.add_middleware(Results(backend=backend))

    # And an actor that waits some amount of time
    condition = Condition()

    @remoulade.actor(store_results=True)
    def wait(n):
        time.sleep(n)
        with condition:
            condition.notify_all()
            return n

    # And this actor is declared
    stub_broker.declare_actor(wait)

    # When I group messages of varying durations together and run the group
    g = group(wait.message(n) for n in range(1, 4))
    g.run()

    # Then every time a job in the group completes, the completed_count should increase
    for count in range(1, len(g) + 1):
        with condition:
            condition.wait(5)
            time.sleep(0.1)  # give the worker time to set the result
            assert g.results.completed_count == count

    # Finally, completed should be true
    assert g.results.completed


@pytest.mark.parametrize("backend", ["redis", "stub"])
@pytest.mark.parametrize("block", [True, False])
def test_group_forget(stub_broker, backend, result_backends, stub_worker, block):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # Given an actor that stores results
    @remoulade.actor(store_results=True)
    def do_work():
        return 42

    # And this actor is declared
    stub_broker.declare_actor(do_work)

    # And I've run a group
    messages = [do_work.message() for _ in range(5)]
    g = group(messages)
    g.run()

    # If i wait for the group to be completed
    if not block:
        stub_broker.join(do_work.queue_name)
        stub_worker.join()

    # If i forget the results
    results = g.results.get(block=block, forget=True)
    assert list(results) == [42] * 5

    # All messages have been forgotten
    for message in messages:
        with pytest.raises(ResultMissing):
            message.result.get()


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_group_wait_forget(stub_broker, backend, result_backends, stub_worker):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # Given an actor that stores results
    @remoulade.actor(store_results=True)
    def do_work():
        return 42

    # And this actor is declared
    stub_broker.declare_actor(do_work)

    # And I've run a group
    messages = [do_work.message() for _ in range(5)]
    g = group(messages)
    g.run()

    # If i forget the results
    g.results.wait(forget=True)

    # All messages have been forgotten
    for message in messages:
        with pytest.raises(ResultMissing):
            message.result.get()


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_pipelines_with_groups(stub_broker, stub_worker, backend, result_backends):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # Given an actor that stores results
    @remoulade.actor(store_results=True)
    def do_work(a):
        return a

    # Given an actor that stores results
    @remoulade.actor(store_results=True)
    def do_sum(results):
        return sum(results)

    # And this actor is declared
    stub_broker.declare_actor(do_work)
    stub_broker.declare_actor(do_sum)

    # When I pipe some messages intended for that actor together and run the pipeline
    pipe = group([do_work.message(12), do_work.message(15)]) | do_sum.message()
    pipe.run()

    result = pipe.result.get(block=True)

    assert 12 + 15 == result

    # Given an actor that stores results
    @remoulade.actor(store_results=True)
    def add(a, b):
        return a + b

    stub_broker.declare_actor(add)

    pipe = do_work.message(13) | group([add.message(12), add.message(15)])
    pipe.run()

    result = pipe.result.get(block=True)

    assert [13 + 12, 13 + 15] == list(result)


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_complex_pipelines(stub_broker, stub_worker, backend, result_backends):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # Given an actor that stores results
    @remoulade.actor(store_results=True)
    def do_work():
        return 1

    # Given an actor that stores results
    @remoulade.actor(store_results=True)
    def add(a):
        return 1 + a

    # Given an actor that stores results
    @remoulade.actor(store_results=True)
    def do_sum(results):
        return sum(results)

    # And this actor is declared
    stub_broker.declare_actor(do_work)
    stub_broker.declare_actor(do_sum)
    stub_broker.declare_actor(add)

    pipe = do_work.message_with_options(pipe_ignore=True) | add.message() | add.message()  # return 3 [1, 2, 3] ?
    g = group([pipe, add.message(), add.message(), do_work.message_with_options(pipe_ignore=True)])  # return [3,2,2,1]
    final_pipe = do_work.message() | g | do_sum.message() | add.message()  # return 9
    final_pipe.run()

    result = final_pipe.result.get(block=True)

    assert 9 == result


@pytest.mark.parametrize("backend", ["redis", "stub"])
def test_pipeline_with_groups_and_pipe_ignore(stub_broker, stub_worker, backend, result_backends):
    # Given a result backend
    backend = result_backends[backend]

    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=backend))

    # Given an actor that do not stores results
    @remoulade.actor()
    def do_work():
        return 1

    @remoulade.actor(store_results=True)
    def do_other_work():
        return 2

    # And this actor is declared
    stub_broker.declare_actor(do_work)
    stub_broker.declare_actor(do_other_work)

    # When I pipe a group with another actor
    pipe = group([do_work.message(), do_work.message()]) | do_other_work.message_with_options(pipe_ignore=True)
    pipe.run()

    # I don't get any error as long the second actor has pipe_ignore=True
    result = pipe.result.get(block=True)

    assert 2 == result

    # But if it don't, the pipeline cannot finish
    pipe = group([do_work.message(), do_work.message()]) | do_other_work.message()
    pipe.run()

    stub_broker.join(do_work.queue_name)
    stub_worker.join()

    with pytest.raises(ResultMissing):
        pipe.result.get()
