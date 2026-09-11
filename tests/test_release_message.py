"""Tests for ReleaseMessage ack control in work()."""

from unittest.mock import MagicMock

import pytest

from command_bus import (
    CommandBus,
    CommandHandler,
    CommandMessage,
    DispatchContext,
    EventBus,
    ReleaseMessage,
    Router,
)
from command_bus.adapters import InMemoryQueueAdapter
from command_bus.interfaces import EventMessage


class PingCommand(CommandMessage):
    value: str


class PingHandler(CommandHandler):
    def process(self, message: CommandMessage):
        return "ok"


class BoomHandler(CommandHandler):
    def process(self, message: CommandMessage):
        raise RuntimeError("boom")


class ReleaseHandler(CommandHandler):
    def process(self, message: CommandMessage):
        raise ReleaseMessage()


class PingEvent(EventMessage):
    value: str


def _bus_with_spy(handler_cls, *, middleware=None):
    adapter = InMemoryQueueAdapter(queue_name="release-test")
    spy = MagicMock(wraps=adapter.dequeue)
    adapter.dequeue = spy
    router = Router()
    router.register(PingCommand, handler_cls)
    bus = CommandBus(
        queue_adapter=adapter,
        command_router=router,
        middleware=middleware,
    )
    return bus, adapter, spy


@pytest.mark.asyncio
async def test_work_acks_on_success():
    bus, adapter, spy = _bus_with_spy(PingHandler)
    await bus.execute(PingCommand(value="a"), wait=False)
    assert await bus.work() == 1
    spy.assert_called_once()


@pytest.mark.asyncio
async def test_work_acks_on_handler_failure():
    bus, adapter, spy = _bus_with_spy(BoomHandler)
    await bus.execute(PingCommand(value="a"), wait=False)
    with pytest.raises(RuntimeError, match="boom"):
        await bus.work()
    spy.assert_called_once()


@pytest.mark.asyncio
async def test_work_skips_ack_on_release_message():
    bus, adapter, spy = _bus_with_spy(ReleaseHandler)
    await bus.execute(PingCommand(value="a"), wait=False)
    assert await bus.work() == 1
    spy.assert_not_called()


@pytest.mark.asyncio
async def test_work_acks_when_middleware_soft_skips():
    async def drop_mw(ctx: DispatchContext, call_next):
        return  # intentional drop — no call_next

    bus, adapter, spy = _bus_with_spy(PingHandler, middleware=[drop_mw])
    await bus.execute(PingCommand(value="a"), wait=False)
    assert await bus.work() == 1
    spy.assert_called_once()


@pytest.mark.asyncio
async def test_work_skips_ack_when_middleware_raises_release():
    async def release_mw(ctx: DispatchContext, call_next):
        raise ReleaseMessage()

    bus, adapter, spy = _bus_with_spy(PingHandler, middleware=[release_mw])
    await bus.execute(PingCommand(value="a"), wait=False)
    assert await bus.work() == 1
    spy.assert_not_called()


@pytest.mark.asyncio
async def test_event_bus_work_skips_ack_on_release_message():
    adapter = InMemoryQueueAdapter(queue_name="event-release")
    spy = MagicMock(wraps=adapter.dequeue)
    adapter.dequeue = spy
    router = Router()

    @router.event()
    def on_ping(value: str) -> None:
        raise ReleaseMessage()

    bus = EventBus(queue_adapter=adapter, command_router=router)
    await bus.publish(on_ping(value="x"))
    assert await bus.work() == 1
    spy.assert_not_called()
