import dramatiq
from dramatiq import Worker
from .common import worker


def test_workers_dont_register_queues_that_arent_whitelisted(stub_broker):
    # Given that I have a worker object with a restricted set of queues
    with worker(stub_broker, queues={"a", "b"}) as stub_worker:
        # When I try to register a consumer for a queue that hasn't been whitelisted
        stub_broker.declare_queue("c")
        stub_broker.declare_queue("c.DQ")

        # Then a consumer should not get spun up for that queue
        assert "c" not in stub_worker.consumers
        assert "c.DQ" not in stub_worker.consumers


def test_worker_doesnt_start_consuming_when_stopped(stub_broker):
    worker = Worker(stub_broker)
    worker.start()
    worker.stop()

    @dramatiq.actor()
    def should_never_run():
        pass

    should_never_run.send()
    for consumer in worker.consumers.values():
        assert not consumer.running


def test_worker_start_not_running_consumers_when_starting(stub_broker):
    worker = Worker(stub_broker)
    worker.start()
    worker.stop()
    has_ran = False

    @dramatiq.actor()
    def should_run():
        nonlocal has_ran
        has_ran = True

    should_run.send()
    worker.start()
    stub_broker.join("default", timeout=100)
    worker.join()

    assert has_ran
