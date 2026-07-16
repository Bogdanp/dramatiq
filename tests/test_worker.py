from __future__ import annotations

import gc
import logging
import time
import weakref
from unittest import mock

import pytest

import dramatiq
import dramatiq.middleware
import dramatiq.worker
from dramatiq.brokers.stub import StubBroker

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


def test_workers_process_messages_in_order(stub_broker) -> None:
    """When worker is running with only one thread, messages are processed in order.

    This is effectively testing messages are pulled from work_queue in a FIFO order."""

    results = []

    @dramatiq.actor()
    def _do_work(value):
        results.append(value)

    try:
        # Worker with one worker, but prefetches 10 messages
        stub_worker = dramatiq.worker.Worker(stub_broker, worker_threads=1)
        stub_worker.queue_prefetch = 10
        stub_worker.start()

        # Pause just worker threads (not consumers) so messages are not removed from worker.work_queue
        for worker_thread in stub_worker.workers:
            worker_thread.pause()
            worker_thread.paused_event.wait()

        # Put 5 messages on the queue
        for i in range(5):
            _do_work.send(i)
            time.sleep(0.001)

        # Check work_queue has 5 messages
        assert stub_worker.work_queue.qsize() == 5

        # Resume worker so messages are processed from work_queue
        stub_worker.resume()
        stub_broker.join(queue_name=_do_work.queue_name)
    finally:
        stub_worker.stop()

    # Check messages were processed in order, i.e. messages came off work_queue in FIFO order.
    assert results == [0, 1, 2, 3, 4]


def test_queue_item_order():
    """Test ordering of the _WorkQueueItem class.

    This is important since this class is used with PriorityQueue.
    """

    @dramatiq.actor()
    def do_work():
        pass

    message1 = do_work.message()
    message2 = do_work.message()

    message_proxy1 = dramatiq.MessageProxy(message1)
    message_proxy2 = dramatiq.MessageProxy(message2)

    # messages/items with different priorities,
    message_1_item_priority_0 = dramatiq.worker._WorkQueueItem(priority=0, message=message_proxy1, _queued_time=0)
    message_2_item_priority_1 = dramatiq.worker._WorkQueueItem(priority=1, message=message_proxy2, _queued_time=0)
    assert message_1_item_priority_0 < message_2_item_priority_1
    assert message_1_item_priority_0 <= message_2_item_priority_1
    assert not message_1_item_priority_0 > message_2_item_priority_1
    assert not message_1_item_priority_0 >= message_2_item_priority_1
    assert message_1_item_priority_0 != message_2_item_priority_1
    assert message_2_item_priority_1 > message_1_item_priority_0
    assert message_2_item_priority_1 >= message_1_item_priority_0
    assert not message_2_item_priority_1 < message_1_item_priority_0
    assert not message_2_item_priority_1 <= message_1_item_priority_0
    assert message_2_item_priority_1 != message_1_item_priority_0

    # messages/items with same priority and different queue times,
    message_1_item_time_0 = dramatiq.worker._WorkQueueItem(priority=0, message=message_proxy1, _queued_time=0)
    message_2_item_time_1 = dramatiq.worker._WorkQueueItem(priority=0, message=message_proxy2, _queued_time=1)
    assert message_1_item_time_0 < message_2_item_time_1
    assert message_1_item_time_0 <= message_2_item_time_1
    assert not message_1_item_time_0 > message_2_item_time_1
    assert not message_1_item_time_0 >= message_2_item_time_1
    assert message_1_item_time_0 != message_2_item_time_1
    assert message_2_item_time_1 > message_1_item_time_0
    assert message_2_item_time_1 >= message_1_item_time_0
    assert not message_2_item_time_1 < message_1_item_time_0
    assert not message_2_item_time_1 <= message_1_item_time_0
    assert message_2_item_time_1 != message_1_item_time_0

    # Messages/items with same priority and queue time
    message_1_item_equal = dramatiq.worker._WorkQueueItem(priority=0, message=message_proxy1, _queued_time=0)
    message_2_item_equal = dramatiq.worker._WorkQueueItem(priority=0, message=message_proxy2, _queued_time=0)
    assert not message_1_item_equal < message_2_item_equal
    assert not message_1_item_equal > message_2_item_equal
    assert message_1_item_equal <= message_2_item_equal
    assert message_1_item_equal >= message_2_item_equal
    assert message_1_item_equal == message_2_item_equal
    assert not message_2_item_equal < message_1_item_equal
    assert not message_2_item_equal > message_1_item_equal
    assert message_2_item_equal <= message_1_item_equal
    assert message_2_item_equal >= message_1_item_equal
    assert message_2_item_equal == message_1_item_equal


def test_exception_from_actor_doesnt_leak(
    stub_broker: StubBroker,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that an Exception raised from an Actor doesn't leak.

    Specifically, test that the Exception is not caught in a reference cycle,
    which would prevent it from being promptly destroyed/deallocated.

    An Exception caught in a reference cycle should still be eventually destroyed
    when the cyclic garbage collector runs (See https://docs.python.org/3/library/gc.html),
    but relying on this is not ideal since memory will be held for longer than needed.

    How does an Exception get caught in a reference cycle?
    This typically happens because the Exception has a Traceback object, which holds a
    reference to each Frame in the stack, which hold references to the local variables
    in each Frame.
    So if any local variable in any Frame references the Exception,
    this creates a reference cycle.
    """

    # Disable log capturing to prevent pytest from holding exception references
    # via captured LogRecord.exc_info
    caplog.set_level(logging.CRITICAL)

    # Keep a weakref to each CustomError object created
    weak_refs: list[weakref.ref[CustomError]] = []

    # Custom Error class for this test
    class CustomError(Exception):
        def __init__(self, *args) -> None:
            super().__init__(*args)
            weak_refs.append(weakref.ref(self))

    # Actor that will raise Exception and fail and retry once.
    @dramatiq.actor(max_retries=1, max_backoff=1)
    def failing_actor():
        raise CustomError()

    try:
        # Disable cyclic GC during the test so that Exceptions caught in reference cycles
        # definitely WON'T be collected / deallocated.
        gc.disable()

        with (
            # Reinstate regular clear_exeption() method
            # so exceptions are not caught in reference cycles.
            mock.patch(
                "dramatiq.brokers.stub._StubMessageProxy.clear_exception",
                new=dramatiq.MessageProxy.clear_exception,
            ),
            worker(stub_broker, worker_timeout=10, worker_threads=1) as stub_worker,
        ):
            # Run actor that will raise an Exception
            failing_actor.send()
            stub_broker.join(failing_actor.queue_name, fail_fast=False)
            stub_worker.join()

        # Check expected number of exception were collected (first run + 1 retry)
        assert len(weak_refs) == 2
        # Check that all CustomErrors raised were deallocated.
        # Because the cyclic Garbage collector is disabled (gc.disable()),
        # If the error is deallocated, it means it must NOT be in any reference cycles.
        for i, weak_ref in enumerate(weak_refs):
            assert weak_ref() is None, f"CustomError object #{i} still alive"

    finally:
        # Re-enable GC after test is finished.
        gc.enable()
