from dramatiq import Worker


def test_workers_dont_register_queues_that_arent_whitelisted(stub_broker):
    # Given that I have a worker object with a restricted set of queues
    worker = Worker(stub_broker, queues={"a", "b"})
    worker.start()

    try:
        # When I try to register a consumer for a queue that hasn't been whitelisted
        stub_broker.declare_queue("c")
        stub_broker.declare_queue("c.DQ")

        # Then a consumer should not get spun up for that queue
        assert "c" not in worker.consumers
        assert "c.DQ" not in worker.consumers
    finally:
        worker.stop()
