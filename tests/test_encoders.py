from __future__ import annotations

import os
import pickle

import pytest

import dramatiq
from dramatiq.encoder import SafePickleEncoder, _SAFE_BUILTINS
from dramatiq.errors import DecodeError


@pytest.fixture
def pickle_encoder():
    old_encoder = dramatiq.get_encoder()
    new_encoder = dramatiq.PickleEncoder()
    dramatiq.set_encoder(new_encoder)
    yield new_encoder
    dramatiq.set_encoder(old_encoder)


@pytest.fixture
def safe_pickle_encoder():
    old_encoder = dramatiq.get_encoder()
    new_encoder = dramatiq.SafePickleEncoder()
    dramatiq.set_encoder(new_encoder)
    yield new_encoder
    dramatiq.set_encoder(old_encoder)


def test_set_encoder_sets_the_global_encoder(pickle_encoder):
    # Given that I've set a Pickle encoder as the global encoder
    # When I get the global encoder
    encoder = dramatiq.get_encoder()

    # Then it should be the same as the encoder that was set
    assert encoder == pickle_encoder


def test_pickle_encoder(pickle_encoder, stub_broker, stub_worker):
    # Given that I've set a Pickle encoder as the global encoder
    # And I have an actor that adds a value to a db
    db = []

    @dramatiq.actor
    def add_value(x):
        db.append(x)

    # When I send that actor a message
    add_value.send(1)

    # And wait on the broker and worker
    stub_broker.join(add_value.queue_name)
    stub_worker.join()

    # Then I expect the message to have been processed
    assert db == [1]


def test_pickle_encoder_emits_deprecation_warning():
    # Given a PickleEncoder
    encoder = dramatiq.PickleEncoder()
    data = encoder.encode({"key": "value"})

    # When I decode data
    # Then a DeprecationWarning should be raised
    with pytest.warns(DeprecationWarning, match="PickleEncoder is deprecated"):
        encoder.decode(data)


# --- SafePickleEncoder tests ---

def test_safe_pickle_encoder_roundtrips_basic_types():
    encoder = SafePickleEncoder()
    data = {
        "queue_name": "default",
        "actor_name": "add",
        "args": [1, 2.5, "hello", True, None],
        "kwargs": {"key": "value"},
        "options": {},
    }
    assert encoder.decode(encoder.encode(data)) == data


def test_safe_pickle_encoder_roundtrips_sets_and_tuples():
    encoder = SafePickleEncoder()
    data = {"items": [1, 2, 3], "frozen": "test"}
    encoded = encoder.encode(data)
    assert encoder.decode(encoded) == data


def test_safe_pickle_encoder_blocks_os_system():
    # Craft a malicious pickle that would call os.system("echo pwned")
    malicious = (
        b"\x80\x04\x95\x1e\x00\x00\x00\x00\x00\x00\x00"
        b"\x8c\x02os\x8c\x06system\x93\x8c\necho pwned\x85R."
    )
    encoder = SafePickleEncoder()
    with pytest.raises(DecodeError, match="os.system.*is not allowed"):
        encoder.decode(malicious)


def test_safe_pickle_encoder_blocks_arbitrary_classes():
    # Build a payload that references os.getcwd (a harmless function,
    # but still not in the allow-list).
    malicious = pickle.dumps(os.getcwd)
    encoder = SafePickleEncoder()
    with pytest.raises(DecodeError):
        encoder.decode(malicious)


def test_safe_pickle_encoder_extra_allowed():
    # Given a SafePickleEncoder with an extra allowed type
    encoder = SafePickleEncoder(extra_allowed={"posixpath.PurePosixPath"})

    # The custom allow-list should be a superset of the defaults
    assert encoder._allowed == _SAFE_BUILTINS | {"posixpath.PurePosixPath"}


def test_safe_pickle_encoder_with_stub_broker(safe_pickle_encoder, stub_broker, stub_worker):
    # Given that I've set a SafePickleEncoder as the global encoder
    # And I have an actor that adds a value to a db
    db = []

    @dramatiq.actor
    def add_value(x):
        db.append(x)

    # When I send that actor a message
    add_value.send(42)

    # And wait on the broker and worker
    stub_broker.join(add_value.queue_name)
    stub_worker.join()

    # Then I expect the message to have been processed
    assert db == [42]


def test_safe_pickle_encoder_is_importable_from_top_level():
    assert hasattr(dramatiq, "SafePickleEncoder")
    assert dramatiq.SafePickleEncoder is SafePickleEncoder
