# This file is a part of Dramatiq.
#
# Copyright (C) 2017,2018 CLEARTYPE SRL <bogdan@cleartype.io>
#
# Dramatiq is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# Dramatiq is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import annotations

import abc
import io
import json
import pickle
import typing
import warnings

from .errors import DecodeError

#: Represents the contents of a Message object as a dict.
MessageData = dict[str, typing.Any]


class Encoder(abc.ABC):
    """Base class for message encoders."""

    @abc.abstractmethod
    def encode(self, data: MessageData) -> bytes:  # pragma: no cover
        """Convert message metadata into a bytestring."""
        raise NotImplementedError

    @abc.abstractmethod
    def decode(self, data: bytes) -> MessageData:  # pragma: no cover
        """Convert a bytestring into message metadata."""
        raise NotImplementedError


class JSONEncoder(Encoder):
    """Encodes messages as JSON.  This is the default encoder."""

    def encode(self, data: MessageData) -> bytes:
        return json.dumps(data, separators=(",", ":")).encode("utf-8")

    def decode(self, data: bytes) -> MessageData:
        try:
            data_str = data.decode("utf-8")
        except UnicodeDecodeError as e:
            raise DecodeError("failed to decode data %r" % (data,), data, e) from None

        try:
            return json.loads(data_str)
        except json.decoder.JSONDecodeError as e:
            raise DecodeError("failed to decode message %r" % (data_str,), data_str, e) from None


class PickleEncoder(Encoder):
    """Pickles messages.

    .. deprecated:: 2.1.1
      :class:`PickleEncoder` deserializes data without restrictions,
      making it vulnerable to remote code execution when a broker is
      compromised.  Use :class:`SafePickleEncoder` instead.
    """

    def encode(self, data: MessageData) -> bytes:
        return pickle.dumps(data)

    def decode(self, data: bytes) -> MessageData:
        warnings.warn(
            "PickleEncoder is deprecated because it is vulnerable to "
            "remote code execution via crafted pickle payloads. Use "
            "SafePickleEncoder instead, which restricts unpickling to "
            "safe built-in types. PickleEncoder will be removed in "
            "dramatiq v3.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return pickle.loads(data)


#: Types that :class:`SafePickleEncoder` allows during unpickling.
_SAFE_BUILTINS: frozenset[str] = frozenset({
    "builtins.True",
    "builtins.False",
    "builtins.None",
    "builtins.int",
    "builtins.float",
    "builtins.complex",
    "builtins.bytes",
    "builtins.bytearray",
    "builtins.str",
    "builtins.tuple",
    "builtins.list",
    "builtins.dict",
    "builtins.set",
    "builtins.frozenset",
    "builtins.slice",
    "builtins.type",
    "builtins.range",
    "builtins.enumerate",
    "datetime.datetime",
    "datetime.date",
    "datetime.time",
    "datetime.timedelta",
    "datetime.timezone",
    "collections.OrderedDict",
    "decimal.Decimal",
    "uuid.UUID",
})


class _RestrictedUnpickler(pickle.Unpickler):
    """Unpickler that only allows a safe set of built-in types."""

    def __init__(self, file: typing.IO[bytes], *, allowed: frozenset[str]) -> None:
        super().__init__(file)
        self._allowed = allowed

    def find_class(self, module: str, name: str) -> type:
        key = f"{module}.{name}"
        if key not in self._allowed:
            raise DecodeError(
                f"Unpickling {key!r} is not allowed. Only built-in "
                f"types are permitted by SafePickleEncoder.",
                key,
                None,
            )
        return super().find_class(module, name)


class SafePickleEncoder(Encoder):
    """Pickles messages using a restricted unpickler.

    Only a fixed set of built-in Python types are allowed during
    deserialization, which prevents remote code execution through
    crafted pickle payloads.

    The default allow-list covers the types typically found in Dramatiq
    message metadata: ``int``, ``float``, ``str``, ``bytes``, ``list``,
    ``dict``, ``tuple``, ``set``, ``frozenset``, ``datetime``,
    ``Decimal``, ``UUID``, and a few others.  You can extend it by
    passing *extra_allowed* to the constructor.

    Parameters:
      extra_allowed: An optional set of ``"module.qualname"`` strings
        for additional types that should be permitted.
    """

    def __init__(self, *, extra_allowed: typing.Iterable[str] = ()) -> None:
        self._allowed: frozenset[str] = _SAFE_BUILTINS | frozenset(extra_allowed)

    def encode(self, data: MessageData) -> bytes:
        return pickle.dumps(data)

    def decode(self, data: bytes) -> MessageData:
        try:
            return _RestrictedUnpickler(io.BytesIO(data), allowed=self._allowed).load()
        except DecodeError:
            raise
        except Exception as e:
            raise DecodeError(
                "failed to decode data %r" % (data,), data, e
            ) from None
