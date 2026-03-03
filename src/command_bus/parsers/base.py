"""Abstract base for message parsers. Implement this to support different message formats."""

from abc import ABC, abstractmethod

from ..interfaces import CommandMessage


class MessageParserBase(ABC):
    """
    Interface for parsing a raw message (e.g. string or bytes) into a CommandMessage.
    Implement this to support different serialization formats (repr-style, JSON, etc.).
    """

    @abstractmethod
    def initialize(self) -> CommandMessage:
        """Parse the raw message and return a CommandMessage instance."""
        ...
