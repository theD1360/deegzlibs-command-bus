"""Tests for async handler dispatch."""

import pytest
from command_bus import CommandBusRouter, CommandMessage, CommandHandler, MessageParser


class AsyncMessage(CommandMessage):
    name: str


class AsyncHandler(CommandHandler):
    async def process(self, message: CommandMessage):
        return f"ok:{message.name}"


@pytest.mark.asyncio
async def test_dispatch_calls_async_handler():
    registry = CommandBusRouter()
    registry.register(AsyncMessage, AsyncHandler)
    parser = MessageParser("tests.test_handler_async.AsyncMessage(name='test')")
    msg = parser.initialize()
    entries = registry.get_handlers_for_message(msg)
    assert len(entries) == 1
    handler = entries[0].handler_instance()
    result = await handler(msg)
    assert result == "ok:test"
