import time
from threading import Condition, Event

import pytest

import dramatiq
from dramatiq import group, middleware, pipeline
from dramatiq.middleware import GroupCallbacks
from dramatiq.results import Results, ResultTimeout


def test_messages_can_be_piped(stub_broker):
    # Given an actor that adds two numbers together
    @dramatiq.actor
    def add(x, y):
        return x + y

    # When I pipe some messages intended for that actor together
    pipe = add.message(1, 2) | add.message(3) | add.message(4)

    # Then I should get back a pipeline object
    assert isinstance(pipe, pipeline)

    # And each message in the pipeline should reference the next message in line
    assert pipe.messages[0].options["pipe_target"] == pipe.messages[1].asdict()
    assert pipe.messages[1].options["pipe_target"] == pipe.messages[2].asdict()
    assert "pipe_target" not in pipe.messages[2].options


def test_pipelines_flatten_child_pipelines(stub_broker):
    # Given an actor that adds two numbers together
    @dramatiq.actor
    def add(x, y):
        return x + y

    # When I pipe a message intended for that actor and another pipeline together
    pipe = pipeline([add.message(1, 2), add.message(3) | add.message(4), add.message(5)])

    # Then the inner pipeline should be flattened into the outer pipeline
    assert len(pipe) == 4
    assert pipe.messages[0].args == (1, 2)
    assert pipe.messages[1].args == (3,)
    assert pipe.messages[2].args == (4,)
    assert pipe.messages[3].args == (5,)


def test_pipe_ignore_applies_to_receiving_message(stub_broker, stub_worker, result_backend):
    # Given a result backend
    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=result_backend))

    @dramatiq.actor(store_results=True)
    def return_args(*args):
        return args

    # When I compose pipe of three messages with pipe_ignore option on second message
    pipe = (
        return_args.message(1) |
        return_args.message_with_options(pipe_ignore=True, args=(2, )) |
        return_args.message(3)
    )

    # And then run and wait for it to complete
    pipe.run()
    stub_broker.join(return_args.queue_name)
    results = list(pipe.get_results())

    # The then result of the first message should NOT be passed as
    # argument to the second message and the result of the second
    # message should be passed as argument to the third message.
    assert results == [[1], [2], [3, [2]]]


def test_pipeline_results_can_be_retrieved(stub_broker, stub_worker, result_backend):
    # Given a result backend
    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=result_backend))

    # And an actor that adds two numbers together and stores the result
    @dramatiq.actor(store_results=True)
    def add(x, y):
        return x + y

    # When I pipe some messages intended for that actor together and run the pipeline
    pipe = add.message(1, 2) | (add.message(3) | add.message(4))
    pipe.run()

    # Then the pipeline result should be the sum of 1, 2, 3 and 4
    assert pipe.get_result(block=True) == 10

    # And I should be able to retrieve individual results
    assert list(pipe.get_results()) == [3, 6, 10]


def test_pipeline_results_respect_timeouts(stub_broker, stub_worker, result_backend):
    # Given a result backend
    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=result_backend))

    # And an actor that waits some amount of time then doubles that amount
    @dramatiq.actor(store_results=True)
    def wait(n):
        time.sleep(n)
        return n * 2

    # When I pipe some messages intended for that actor together and run the pipeline
    pipe = wait.message(1) | wait.message() | wait.message()
    pipe.run()

    # And get the results with a lower timeout than the tasks can complete in
    # Then a ResultTimeout error should be raised
    with pytest.raises(ResultTimeout):
        for _ in pipe.get_results(block=True, timeout=1000):
            pass


def test_pipelines_expose_completion_stats(stub_broker, stub_worker, result_backend):
    # Given a result backend
    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=result_backend))

    # And an actor that waits some amount of time
    condition = Condition()

    @dramatiq.actor(store_results=True)
    def wait(n):
        time.sleep(n)
        with condition:
            condition.notify_all()
            return n

    # When I pipe some messages intended for that actor together and run the pipeline
    pipe = wait.message(1) | wait.message()
    pipe.run()

    # Then every time a job in the pipeline completes, the completed_count should increase
    for count in range(1, len(pipe) + 1):
        with condition:
            condition.wait(2)
            time.sleep(0.1)  # give the worker time to set the result
            assert pipe.completed_count == count

    # Finally, completed should be true
    assert pipe.completed


def test_pipelines_can_be_incomplete(stub_broker, result_backend):
    # Given that I am not running a worker
    # And I have a result backend
    stub_broker.add_middleware(Results(backend=result_backend))

    # And I have an actor that does nothing
    @dramatiq.actor(store_results=True)
    def do_nothing():
        return None

    # And I've run a pipeline
    pipe = do_nothing.message() | do_nothing.message_with_options(pipe_ignore=True)
    pipe.run()

    # When I check if the pipeline has completed
    # Then it should return False
    assert not pipe.completed


def test_groups_execute_jobs_in_parallel(stub_broker, stub_worker, result_backend):
    # Given that I have a result backend
    stub_broker.add_middleware(Results(backend=result_backend))

    # And I have an actor that sleeps for 100ms
    @dramatiq.actor(store_results=True)
    def wait():
        time.sleep(0.1)

    # When I group multiple of these actors together and run them
    t = time.monotonic()
    g = group([wait.message() for _ in range(5)])
    g.run()

    # And wait on the group to complete
    results = list(g.get_results(block=True))

    # Then the total elapsed time should be less than 500ms
    assert time.monotonic() - t <= 0.5

    # And I should get back as many results as there were jobs in the group
    assert len(results) == len(g)

    # And the group should be completed
    assert g.completed


def test_groups_execute_inner_groups(stub_broker, stub_worker, result_backend):
    # Given that I have a result backend
    stub_broker.add_middleware(Results(backend=result_backend))

    # And I have an actor that sleeps for 100ms
    @dramatiq.actor(store_results=True)
    def wait():
        time.sleep(0.1)

    # When I group multiple groups inside one group and run it
    t = time.monotonic()
    g = group(group(wait.message() for _ in range(2)) for _ in range(3))
    g.run()

    # And wait on the group to complete
    results = list(g.get_results(block=True))

    # Then the total elapsed time should be less than 500ms
    assert time.monotonic() - t <= 0.5

    # And I should get back 3 results each with 2 results inside it
    assert results == [[None, None]] * 3

    # And the group should be completed
    assert g.completed


def test_groups_can_time_out(stub_broker, stub_worker, result_backend):
    # Given that I have a result backend
    stub_broker.add_middleware(Results(backend=result_backend))

    # And I have an actor that sleeps for 300ms
    @dramatiq.actor(store_results=True)
    def wait():
        time.sleep(0.3)

    # When I group a few jobs together and run it
    g = group(wait.message() for _ in range(2))
    g.run()

    # And wait for the group to complete with a timeout
    # Then a ResultTimeout error should be raised
    with pytest.raises(ResultTimeout):
        g.wait(timeout=100)

    # And the group should not be completed
    assert not g.completed


def test_groups_expose_completion_stats(stub_broker, stub_worker, result_backend):
    # Given that I have a result backend
    stub_broker.add_middleware(Results(backend=result_backend))

    # And an actor that waits some amount of time
    condition = Condition()

    @dramatiq.actor(store_results=True)
    def wait(n):
        time.sleep(n)
        with condition:
            condition.notify_all()
            return n

    # When I group messages of varying durations together and run the group
    g = group(wait.message(n) for n in range(1, 4))
    g.run()

    # Then every time a job in the group completes, the completed_count should increase
    for count in range(1, len(g) + 1):
        with condition:
            condition.wait(5)
            time.sleep(0.1)  # give the worker time to set the result
            assert g.completed_count == count

    # Finally, completed should be true
    assert g.completed


def test_pipeline_does_not_continue_to_next_actor_when_message_is_marked_as_failed(stub_broker, stub_worker):
    # Given that I have an actor that fails messages
    class FailMessageMiddleware(middleware.Middleware):
        def after_process_message(self, broker, message, *, result=None, exception=None):
            message.fail()

    stub_broker.add_middleware(FailMessageMiddleware())

    has_run = False

    @dramatiq.actor
    def do_nothing():
        pass

    @dramatiq.actor
    def should_never_run():
        nonlocal has_run
        has_run = True

    # When I pipe some messages intended for that actor together and run the pipeline
    pipe = do_nothing.message_with_options(pipe_ignore=True) | should_never_run.message()
    pipe.run()

    stub_broker.join(should_never_run.queue_name, timeout=10 * 1000)
    stub_worker.join()

    # Then the second message in the pipe should never have run
    assert not has_run


def test_pipeline_respects_own_delay(stub_broker, stub_worker, result_backend):
    # Given a result backend
    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=result_backend))

    # And an actor that adds two numbers together
    @dramatiq.actor(store_results=True)
    def add(x, y):
        return x + y

    # When I pipe some messages intended for that actor together and run the pipeline with a delay
    pipe = add.message(1, 2) | add.message(3)
    pipe.run(delay=10000)

    # And get the results with a lower timeout than the the pipeline is delayed by
    # Then a ResultTimeout error should be raised
    with pytest.raises(ResultTimeout):
        for _ in pipe.get_results(block=True, timeout=100):
            pass


def test_pipeline_respects_delay_of_first_message(stub_broker, stub_worker, result_backend):
    # Given a result backend
    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=result_backend))

    # And an actor that adds two numbers together
    @dramatiq.actor(store_results=True)
    def add(x, y):
        return x + y

    # When I pipe some messages intended for that actor together, where first message is delayed and run the pipeline
    pipe = add.message_with_options(args=(1, 2), delay=10000) | add.message(3)
    pipe.run()

    # And get the results with a lower timeout than the first message's delay
    # Then a ResultTimeout error should be raised
    with pytest.raises(ResultTimeout):
        for _ in pipe.get_results(block=True, timeout=100):
            pass


def test_pipeline_respects_delay_of_second_message(stub_broker, stub_worker, result_backend):
    # Given a result backend
    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=result_backend))

    # And an actor that adds two numbers together
    @dramatiq.actor(store_results=True)
    def add(x, y):
        return x + y

    # When I pipe some messages intended for that actor together, where second message is delayed and run the pipeline
    pipe = add.message(1, 2) | add.message_with_options(args=(3,), delay=10000)
    pipe.run()

    # And get the results with a lower timeout than the second message's delay
    # Then a ResultTimeout error should be raised
    with pytest.raises(ResultTimeout):
        for _ in pipe.get_results(block=True, timeout=100):
            pass


def test_pipeline_respects_bigger_of_first_messages_and_pipelines_delay(stub_broker, stub_worker, result_backend):
    # Given a result backend
    # And a broker with the results middleware
    stub_broker.add_middleware(Results(backend=result_backend))

    # And an actor that adds two numbers together
    @dramatiq.actor(store_results=True)
    def add(x, y):
        return x + y

    # When I pipe some messages intended for that actor together, first of which is delayed
    # And the pipeline is delayed with a bigger value than the first message, and run the pipeline
    pipe = add.message_with_options(args=(1, 2), delay=100) | add.message(3)
    pipe.run(delay=10000)

    # And get the results with a higher timeout than first message's delay, but lower than pipeline's delay
    # Then a ResultTimeout error should be raised
    with pytest.raises(ResultTimeout):
        for _ in pipe.get_results(block=True, timeout=300):
            pass


def test_groups_can_have_completion_callbacks(stub_broker, stub_worker, rate_limiter_backend):
    # Given that I have a rate limiter backend
    # And I've added the GroupCallbacks middleware to my broker
    stub_broker.add_middleware(GroupCallbacks(rate_limiter_backend))

    do_nothing_times = []
    finalize_times = []
    finalized = Event()

    @dramatiq.actor
    def do_nothing():
        do_nothing_times.append(time.monotonic())

    @dramatiq.actor
    def finalize(n):
        assert n == 42
        finalize_times.append(time.monotonic())
        finalized.set()

    # When I group together some messages with a completion callback
    g = group(do_nothing.message() for n in range(5))
    g.add_completion_callback(finalize.message(42))
    g.run()

    # And wait for the callback to be callled
    finalized.wait(timeout=30)

    # Then all the messages in the group should run
    assert len(do_nothing_times) == 5

    # And the callback
    assert len(finalize_times) == 1

    # And the callback should run after all the messages
    assert sorted(do_nothing_times)[-1] <= finalize_times[0]


def test_groups_with_completion_callbacks_fail_unless_group_callbacks_is_set_up(stub_broker, stub_worker):
    # Given that I haven't set up GroupCallbacks
    @dramatiq.actor
    def do_nothing():
        pass

    @dramatiq.actor
    def finalize(n):
        pass

    # When I group together some messages with a completion callback
    g = group(do_nothing.message() for n in range(5))
    g.add_completion_callback(finalize.message(42))

    # And run the group
    # Then a RuntimeError should be raised
    with pytest.raises(RuntimeError):
        g.run()


def test_groups_of_pipelines_can_have_completion_callbacks(stub_broker, stub_worker, rate_limiter_backend):
    # Given that I have a rate limiter backend
    # And I've added the GroupCallbacks middleware to my broker
    stub_broker.add_middleware(GroupCallbacks(rate_limiter_backend))

    do_nothing_times = []
    finalize_times = []
    finalized = Event()

    @dramatiq.actor
    def do_nothing(_):
        do_nothing_times.append(time.monotonic())

    @dramatiq.actor
    def finalize(n):
        assert n == 42
        finalize_times.append(time.monotonic())
        finalized.set()

    # When I group together some messages with a completion callback
    g = group([
        do_nothing.message(1) | do_nothing.message(),
        do_nothing.message(1)
    ])
    g.add_completion_callback(finalize.message(42))
    g.run()

    # And wait for the callback to be callled
    finalized.wait(timeout=30)

    # Then all the messages in the group should run
    assert len(do_nothing_times) == 3

    # And the callback
    assert len(finalize_times) == 1

    # And the callback should run after all the messages
    assert sorted(do_nothing_times)[-1] <= finalize_times[0]
