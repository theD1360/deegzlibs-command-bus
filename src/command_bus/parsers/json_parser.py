"""Parser for JSON message payloads."""

import json
from typing import Any, Dict

from ..interfaces import CommandMessage
from ..utils import ModuleImporter
from .base import MessageParserBase


class JsonMessageParser(MessageParserBase):
    """
    Parses JSON strings into CommandMessage instances.

    Expected format: a JSON object with a type field that holds the fully
    qualified message class name (module.path.ClassName). The remaining
    keys are passed as keyword arguments to that class.

    Example:
        {"__type__": "mymodule.events.OrderCreated", "order_id": "abc", "amount_cents": 1999}

    The type key is configurable via the constructor (default: "__type__").
    """

    def __init__(
        self,
        message_string: str,
        type_key: str = "__type__",
    ) -> None:
        self._payload: Dict[str, Any] = json.loads(message_string)
        self._type_key = type_key

    def initialize(self) -> CommandMessage:
        """Parse the JSON and return a CommandMessage instance."""
        payload = dict(self._payload)
        type_value = payload.pop(self._type_key, None)
        if type_value is None:
            raise ValueError(
                f"JSON message must contain a '{self._type_key}' field with the "
                "fully qualified message class name (e.g. module.path.ClassName)"
            )
        if not isinstance(type_value, str):
            raise ValueError(
                f"'{self._type_key}' must be a string, got {type(type_value)}"
            )

        module_path, _, class_name = type_value.rpartition(".")
        if not module_path or not class_name:
            raise ValueError(
                f"'{self._type_key}' must be a fully qualified class name "
                "(e.g. mymodule.events.OrderCreated), got {type_value!r}"
            )

        importer = ModuleImporter(module_path)
        message_class = importer.get_class(class_name)
        if not issubclass(message_class, CommandMessage):
            raise ValueError(f"Class {type_value!r} is not a CommandMessage subclass")
        return message_class(**payload)
