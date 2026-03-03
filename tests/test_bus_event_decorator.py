"""Tests for router.command() + bus.execute() with the constructed CommandMessage class."""

import asyncio
from unittest.mock import MagicMock

import pytest
from command_bus import CommandBus, CommandBusRouter
from command_bus.adapters import (
    InMemoryCommandBusAdapter,
    InMemoryResponseStore,
    SqsCommandBusAdapter,
)


@pytest.mark.asyncio
async def test_router_command_call_returns_message_for_bus_execute():
    """Calling the decorated function returns the message; pass it to bus.execute()."""
    adapter = MagicMock(spec=SqsCommandBusAdapter)
    router = CommandBusRouter()
    bus = CommandBus(queue_adapter=adapter, command_router=router)

    @router.command()
    def on_created(order_id: str, amount_cents: int):
        return {"order_id": order_id}

    await bus.execute(on_created(order_id="ord-1", amount_cents=2000), wait=False)
    assert adapter.enqueue.called
    (msg,) = adapter.enqueue.call_args[0]
    assert msg.order_id == "ord-1"
    assert msg.amount_cents == 2000


@pytest.mark.asyncio
async def test_router_command_message_class_works_with_execute_and_wait():
    """get_price(...) returns the message; pass to execute(wait=True)."""
    adapter = MagicMock()
    store = InMemoryResponseStore()
    router = CommandBusRouter()
    bus = CommandBus(
        queue_adapter=adapter,
        command_router=router,
        response_store=store,
    )

    @router.command()
    def get_price(product_id: str) -> dict:
        return {"price_cents": 99, "product_id": product_id}

    async def run_client():
        return await bus.execute(
            get_price(product_id="p1"), timeout_seconds=2, poll_interval_seconds=0.05
        )

    async def simulate_worker():
        await asyncio.sleep(0.1)
        enqueued = adapter.enqueue.call_args[0][0]
        store.set(
            enqueued.correlation_id,
            {"price_cents": 99, "product_id": "p1"},
            ttl_seconds=60,
        )

    client_task = asyncio.create_task(run_client())
    await simulate_worker()
    result = await client_task
    assert result == {"price_cents": 99, "product_id": "p1"}


@pytest.mark.asyncio
async def test_router_command_then_bus_execute_and_work():
    """Full flow: bus.execute(on_created(...), wait=False) and bus.work()."""
    adapter = InMemoryCommandBusAdapter(queue_name="commands")
    router = CommandBusRouter()
    bus = CommandBus(queue_adapter=adapter, command_router=router)
    received: list[str] = []

    @router.command()
    def on_created(order_id: str, amount_cents: int):
        received.append(order_id)

    await bus.execute(on_created(order_id="a", amount_cents=1), wait=False)
    await bus.execute(on_created(order_id="b", amount_cents=2), wait=False)
    await bus.work()
    await bus.work()
    assert received == ["a", "b"]
