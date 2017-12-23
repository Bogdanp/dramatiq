import abc
import json
import pickle
import typing


#: Represents the contents of a Message object as a dict.
MessageData = typing.Dict[str, typing.Any]


class Encoder(abc.ABC):
    """Base class for message encoders.
    """

    @abc.abstractmethod
    def encode(self, data: MessageData) -> bytes:  # pragma: no cover
        """Convert message metadata into a bytestring.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def decode(self, data: bytes) -> MessageData:  # pragma: no cover
        """Convert a bytestring into message metadata.
        """
        raise NotImplementedError


class JSONEncoder(Encoder):
    """Encodes messages as JSON.  This is the default encoder.
    """

    def encode(self, data: MessageData) -> bytes:
        return json.dumps(data, separators=(",", ":")).encode("utf-8")

    def decode(self, data: bytes) -> MessageData:
        return json.loads(data.decode("utf-8"))


class PickleEncoder(Encoder):
    """Pickles messages.

    Warning:
      This encoder is not secure against maliciously-constructed data.
      Use it at your own risk.
    """

    encode = pickle.dumps
    decode = pickle.loads
