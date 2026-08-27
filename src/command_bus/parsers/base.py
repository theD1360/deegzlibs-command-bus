"""Abstract base for message parsers. Implement this to support different message formats."""

from abc import ABC, abstractmethod
from typing import Dict, Optional

from ..interfaces import TransmissibleBaseModel

# Transport message attributes shape (e.g. SNS MessageAttributes):
# name -> {DataType, StringValue}
MessageAttributes = Dict[str, Dict[str, str]]


class MessageParserBase(ABC):
    """
    Bidirectional message parser for queue and SNS transports.

    Inbound: ``Parser(raw_string).initialize() -> TransmissibleBaseModel``
    Outbound: ``Parser.dumps(message) -> str``

    Subclasses may override optional publish hooks: ``subject`` and
    ``message_attributes``. Defaults preserve backward-compatible repr
    serialization and plain publish (body only).
    """

    @abstractmethod
    def initialize(self) -> TransmissibleBaseModel:
        """Parse the raw message and return a message instance."""
        ...

    @classmethod
    def dumps(cls, message: TransmissibleBaseModel) -> str:
        """Serialize a message for transport. Default: repr-style ``str(message)``."""
        return str(message)

    @classmethod
    def subject(
        cls,
        message: TransmissibleBaseModel,
        encoded_body: str,
    ) -> Optional[str]:
        """Publish subject for this message, or None to omit."""
        return None

    @classmethod
    def message_attributes(
        cls,
        message: TransmissibleBaseModel,
        encoded_body: str,
    ) -> Optional[MessageAttributes]:
        """Publish message attributes for this message, or None to omit."""
        return None
