"""Tests for command_bus registry."""

from typing import Optional

import pytest
from command_bus import (
    CommandBusRouter,
    CommandBusRouterEntry,
    CommandMessage,
    CommandHandler,
    get_qual_name,
)


class SampleMessage(CommandMessage):
    value: int


class SampleHandler(CommandHandler):
    def process(self, message: CommandMessage):
        return message.value


def test_get_qual_name_class():
    assert get_qual_name(SampleMessage) == "tests.test_registry.SampleMessage"


def test_get_qual_name_instance():
    m = SampleMessage(value=1)
    assert get_qual_name(m) == "tests.test_registry.SampleMessage"


def test_registry_register_and_get_handlers():
    registry = CommandBusRouter()
    registry.register(SampleMessage, SampleHandler)
    entries = registry.get_handlers_for_message(SampleMessage)
    assert len(entries) == 1
    assert entries[0].handler_class is SampleHandler
    assert entries[0].message_class is SampleMessage


def test_registry_get_handlers_by_instance():
    registry = CommandBusRouter()
    registry.register(SampleMessage, SampleHandler)
    m = SampleMessage(value=2)
    entries = registry.get_handlers_for_message(m)
    assert len(entries) == 1


def test_registry_deregister():
    registry = CommandBusRouter()
    registry.register(SampleMessage, SampleHandler)
    registry.deregister(SampleMessage, SampleHandler)
    entries = registry.get_handlers_for_message(SampleMessage)
    assert len(entries) == 0


def test_registry_entry_handler_instance():
    entry = CommandBusRouterEntry(
        message_class=SampleMessage,
        handler_class=SampleHandler,
    )
    handler = entry.handler_instance()
    assert isinstance(handler, SampleHandler)


def test_registry_entry_is_message_match():
    entry = CommandBusRouterEntry(
        message_class=SampleMessage,
        handler_class=SampleHandler,
    )
    assert entry.is_message_match(SampleMessage) is True
    assert entry.is_message_match(SampleMessage(value=1)) is True
    assert entry.is_message_match(entry.message_qual_name) is True
    assert entry.is_message_match("other.Module.OtherMessage") is False


def test_registry_command_decorator_creates_message_from_params():
    """@router.command() creates CommandMessage from function params; calling the decorator returns the message."""
    router = CommandBusRouter()
    received: list[dict] = []

    @router.command()
    def on_order_created(order_id: str, amount_cents: int):
        received.append({"order_id": order_id, "amount_cents": amount_cents})

    assert hasattr(on_order_created, "_command_message_class")
    assert on_order_created._command_message_class.__name__ == "on_order_createdMessage"
    entries = router.get_handlers_for_message(on_order_created._command_message_class)
    assert len(entries) == 1
    handler = entries[0].handler_instance()
    msg = on_order_created(
        order_id="ord-1", amount_cents=1000
    )  # returns message instance
    handler.process(msg)
    assert received == [{"order_id": "ord-1", "amount_cents": 1000}]


def test_registry_command_decorator_returns_message_factory():
    """Decorator returns a callable that builds the message; call it and pass to handler."""
    router = CommandBusRouter()

    @router.command()
    def my_handler(x: int) -> int:
        return x + 1

    # Calling the decorator returns the message instance (prefilled)
    msg = my_handler(10)
    assert msg.x == 10
    handler_inst = router.get_handlers_for_message(my_handler._command_message_class)[
        0
    ].handler_instance()
    assert handler_inst.process(msg) == 11


@pytest.mark.asyncio
async def test_registry_command_decorator_async_handler():
    """@router.command() works with async functions; handler.__call__ awaits process()."""
    router = CommandBusRouter()
    received: list[str] = []

    @router.command()
    async def on_created(name: str) -> str:
        received.append(name)
        return f"ok:{name}"

    msg = on_created(name="test")  # returns message instance
    entries = router.get_handlers_for_message(on_created._command_message_class)
    assert len(entries) == 1
    handler = entries[0].handler_instance()
    result = await handler(msg)
    assert result == "ok:test"
    assert received == ["test"]


def test_registry_command_decorator_optional_and_default_params():
    """Generated message supports Optional and default parameter values."""
    router = CommandBusRouter()

    @router.command()
    def handle(tag: str, count: int = 0, extra: Optional[str] = None) -> str:
        return f"{tag}:{count}:{extra!r}"

    handler = router.get_handlers_for_message(handle._command_message_class)[
        0
    ].handler_instance()
    msg1 = handle(tag="a")
    assert handler.process(msg1) == "a:0:None"
    msg2 = handle(tag="b", count=2, extra="x")
    assert handler.process(msg2) == "b:2:'x'"
