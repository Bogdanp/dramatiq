import time
from unittest.mock import Mock

import pytest

import remoulade
from remoulade import QueueJoinTimeout, QueueNotFound


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
    @remoulade.actor
    def do_work():
        pass

    # And this actor is declared
    stub_broker.declare_actor(do_work)

    # When I send that actor a message
    do_work.send()

    # Then its queue should contain a message
    assert stub_broker.queues[do_work.queue_name].qsize() == 1

    # When I flush all the queues in the broker
    stub_broker.flush_all()

    # Then the queue should be empty and it should contain no in-progress tasks
    assert stub_broker.queues[do_work.queue_name].qsize() == 0
    assert stub_broker.queues[do_work.queue_name].unfinished_tasks == 0


def test_stub_broker_can_join_with_timeout(stub_broker, stub_worker):
    # Given that I have an actor that takes a long time to run
    @remoulade.actor
    def do_work():
        time.sleep(1)

    # And this actor is declared
    stub_broker.declare_actor(do_work)

    # When I send that actor a message
    do_work.send()

    # And join on its queue with a timeout
    # Then I expect a QueueJoinTimeout to be raised
    with pytest.raises(QueueJoinTimeout):
        stub_broker.join(do_work.queue_name, timeout=500)
