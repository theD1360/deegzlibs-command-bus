"""Optional message codecs for wrapping parser payloads (e.g. JSON)."""

import base64
import gzip
from abc import ABC, abstractmethod
from typing import List, Optional, Sequence


class MessageCodec(ABC):
    """Encode and decode a string payload before/after parser processing."""

    @abstractmethod
    def encode(self, payload: str) -> str:
        """Wrap a payload for transport."""
        ...

    @abstractmethod
    def decode(self, wrapped: str) -> str:
        """Unwrap a transported payload."""
        ...


class IdentityMessageCodec(MessageCodec):
    """No-op codec."""

    def encode(self, payload: str) -> str:
        return payload

    def decode(self, wrapped: str) -> str:
        return wrapped


class Base64MessageCodec(MessageCodec):
    """Base64-encode UTF-8 payloads."""

    def encode(self, payload: str) -> str:
        return base64.b64encode(payload.encode("utf-8")).decode("ascii")

    def decode(self, wrapped: str) -> str:
        return base64.b64decode(wrapped).decode("utf-8")


class GzipMessageCodec(MessageCodec):
    """Gzip-compress UTF-8 payloads (binary stored as a latin-1 string)."""

    def encode(self, payload: str) -> str:
        return gzip.compress(payload.encode("utf-8")).decode("latin-1")

    def decode(self, wrapped: str) -> str:
        return gzip.decompress(wrapped.encode("latin-1")).decode("utf-8")


class ChainedMessageCodec(MessageCodec):
    """Apply multiple codecs in order when encoding; reverse order when decoding."""

    def __init__(self, codecs: Sequence[MessageCodec]) -> None:
        self._codecs: List[MessageCodec] = list(codecs)

    def encode(self, payload: str) -> str:
        result = payload
        for codec in self._codecs:
            result = codec.encode(result)
        return result

    def decode(self, wrapped: str) -> str:
        result = wrapped
        for codec in reversed(self._codecs):
            result = codec.decode(result)
        return result


def configure_json_parser(
    codec: Optional[MessageCodec] = None,
    type_key: str = "__type__",
):
    """
    Return a JsonMessageParser subclass bound to optional codec settings.

    Use as ``message_parser_class`` on CommandBus / EventBus:

        bus = CommandBus(
            queue_adapter=adapter,
            message_parser_class=configure_json_parser(codec=Base64MessageCodec()),
        )
    """

    from .json_parser import JsonMessageParser

    class ConfiguredJsonMessageParser(JsonMessageParser):
        def __init__(self, message_string: str) -> None:
            super().__init__(message_string, type_key=type_key, codec=codec)

    ConfiguredJsonMessageParser.__name__ = "JsonMessageParser"
    ConfiguredJsonMessageParser.__qualname__ = "JsonMessageParser"
    return ConfiguredJsonMessageParser
