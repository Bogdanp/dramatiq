import dramatiq
import pytest

from dramatiq import QueueNotFound
from unittest.mock import Mock


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

    # If I send that actor a message
    do_work.send()

    # I expect its queue to contain a message
    assert stub_broker.queues[do_work.queue_name].qsize() == 1

    # If I then flush all the queues in the broker
    stub_broker.flush_all()

    # I expect the queue to have been emptied
    assert stub_broker.queues[do_work.queue_name].qsize() == 0
