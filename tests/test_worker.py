from __future__ import annotations

from queue import PriorityQueue

from dramatiq.broker import MessageProxy
from dramatiq.message import Message
from dramatiq.worker import ConsumerThread

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


def test_delayed_messages_use_consumer_promotion_hook():
    # Given that I have a consumer that can atomically promote delayed messages
    class Broker:
        def __init__(self):
            self.enqueued_messages = []

        def enqueue(self, message):
            self.enqueued_messages.append(message)

    class Consumer:
        def __init__(self):
            self.promoted_messages = []

        def enqueue_from_delay_queue(self, message):
            self.promoted_messages.append(message)
            return True

    broker = Broker()
    consumer = Consumer()
    consumer_thread = ConsumerThread(
        broker=broker,
        queue_name="default.DQ",
        prefetch=1,
        work_queue=PriorityQueue(),
        worker_timeout=100,
    )
    consumer_thread.consumer = consumer

    message = MessageProxy(
        Message(
            queue_name="default.DQ",
            actor_name="actor",
            args=(),
            kwargs={},
            options={"eta": 0, "redis_message_id": "redis-message-id"},
        )
    )
    consumer_thread.delay_queue.put((0, message))

    # When delayed messages are handled
    consumer_thread.handle_delayed_messages()

    # Then the consumer-specific promotion hook should be used instead of
    # a generic enqueue followed by a separate ack.
    assert consumer.promoted_messages == [message]
    assert broker.enqueued_messages == []
