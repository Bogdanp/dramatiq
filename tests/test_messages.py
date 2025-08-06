from __future__ import annotations

from datetime import datetime, timedelta, timezone

import dramatiq


def test_messages_have_namedtuple_methods(stub_broker):
    @dramatiq.actor
    def add(x, y):
        return x + y

    msg1 = add.message(1, 2)
    assert msg1.asdict() == msg1._asdict()

    assert msg1._field_defaults == {}
    assert msg1._fields == (
        "queue_name",
        "actor_name",
        "args",
        "kwargs",
        "options",
        "message_id",
        "message_timestamp",
    )

    msg2 = msg1._replace(queue_name="example")
    assert msg2._asdict()["queue_name"] == "example"


def test_messageproxy_representation(stub_broker):
    """Ensure that MessageProxy defines ``__repr__``.

    While Dramatiq logs messages and MessageProxies formatted using the "%s" placeholder, other tools like Sentry-SDK
    force ``repr`` of any log param that isn't a primitive. This means that MessageProxy has to implement ``__repr__``
    in order for the captured messages to be more helpful than:

    > Failed to process message <dramatiq.broker.MessageProxy object at 0x74522262a950> with unhandled exception.
    """

    @dramatiq.actor
    def actor(arg):
        return arg

    message = actor.send("input")

    consumer = stub_broker.consume("default")
    message_proxy = next(consumer)

    assert repr(message) in repr(message_proxy), "Expecting MessageProxy repr to contain Message repr"
    assert str(message) == str(message_proxy), "Expecting identical __str__ of MessageProxy and Message"


def test_message_datetime(stub_broker):
    """Test reading message time as datetime."""

    @dramatiq.actor
    def actor(arg):
        return arg

    message = actor.send("input")
    after = datetime.now(timezone.utc)

    assert message.message_datetime.tzinfo is timezone.utc
    assert message.message_datetime < after
    assert message.message_datetime > after - timedelta(seconds=1)

    # no rounding problems here because message_timestamp is an int
    assert message.message_datetime.timestamp() == message.message_timestamp / 1000
