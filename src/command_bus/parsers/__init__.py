"""
Message parsers: pluggable parsers for different message formats.

Use MessageParser (repr-style) by default, JsonMessageParser for JSON,
Base64MessageParser for base64-encoded (optionally compressed) payloads,
MessageCodec wrappers for JSON, or implement MessageParserBase for other formats.
"""

from .base import MessageParserBase, MessageAttributes
from .base64_parser import Base64MessageParser
from .codec import (
    Base64MessageCodec,
    ChainedMessageCodec,
    GzipMessageCodec,
    IdentityMessageCodec,
    MessageCodec,
    configure_json_parser,
)
from .json_parser import JsonMessageParser
from .repr_parser import ReprMessageParser

# Default / backward-compatible name for the repr-style parser
MessageParser = ReprMessageParser

__all__ = [
    "Base64MessageCodec",
    "Base64MessageParser",
    "ChainedMessageCodec",
    "GzipMessageCodec",
    "IdentityMessageCodec",
    "JsonMessageParser",
    "MessageCodec",
    "MessageParser",
    "MessageParserBase",
    "MessageAttributes",
    "ReprMessageParser",
    "configure_json_parser",
]
