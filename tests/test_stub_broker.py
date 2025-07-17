from __future__ import annotations

import time
from unittest.mock import Mock

import pytest

import dramatiq
from dramatiq import QueueJoinTimeout, QueueNotFound


def test_stub_broker_raises_queue_error_when_consuming_undeclared_queues(stub_broker):
    # Given that I have a stub broker
    # If I attempt to consume a queue that wasn't declared
    # I expect a QueueNotFound error to be raised
    with pytest.raises(QueueNotFound):
        stub_broker.consume("idontexist")


def test_stub_broker_raises_queue_error_when_enqueueing_messages_on_undeclared_queues(stub_broker):
    # Given that I have a stub broker
    # If I attempt to enqueue a message on a queue that wasn't declared
    # I expect a QueueNotFound error to be raised
    with pytest.raises(QueueNotFound):
        stub_broker.enqueue(Mock(queue_name="idontexist"))


def test_stub_broker_raises_queue_error_when_joining_on_undeclared_queues(stub_broker):
    # Given that I have a stub broker
    # If I attempt to join on a queue that wasn't declared
    # I expect a QueueNotFound error to be raised
    with pytest.raises(QueueNotFound):
        stub_broker.join("idontexist")


def test_stub_broker_can_be_flushed(stub_broker):
    # Given that I have an actor
    @dramatiq.actor
    def do_work():
        pass

    # When I send that actor a message
    do_work.send()

    # And when there is already a message on that actor's dead-letter queue
    stub_broker.dead_letters_by_queue[do_work.queue_name].append("dead letter")

    # Then its queue should contain the right number of messages
    assert stub_broker.queues[do_work.queue_name].qsize() == 1
    assert len(stub_broker.dead_letters) == 1

    # When I flush all of the queues
    stub_broker.flush_all()

    # Then the queue should be empty
    assert stub_broker.queues[do_work.queue_name].qsize() == 0
    # and it should contain no in-progress tasks
    assert stub_broker.queues[do_work.queue_name].unfinished_tasks == 0
    # and the dead-letter queue should be empty
    assert len(stub_broker.dead_letters) == 0


def test_stub_broker_can_join_with_timeout(stub_broker, stub_worker):
    # Given that I have an actor that takes a long time to run
    @dramatiq.actor
    def do_work():
        time.sleep(1)

    # When I send that actor a message
    do_work.send()

    # And join on its queue with a timeout
    # Then I expect a QueueJoinTimeout to be raised
    with pytest.raises(QueueJoinTimeout):
        stub_broker.join(do_work.queue_name, timeout=500)


def test_stub_broker_join_reraises_actor_exceptions_in_the_joining_current_thread(stub_broker, stub_worker):
    # Given that I have an actor that always fails with a custom exception
    class CustomError(Exception):
        pass

    @dramatiq.actor(max_retries=0)
    def do_work():
        raise CustomError("well, shit")

    # When I send that actor a message
    do_work.send()

    # And join on its queue
    # Then that exception should be raised in my thread
    with pytest.raises(CustomError):
        stub_broker.join(do_work.queue_name, fail_fast=True)
