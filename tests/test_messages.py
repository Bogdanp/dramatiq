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
