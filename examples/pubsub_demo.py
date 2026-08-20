#!/usr/bin/env python3
"""
Minimal pub/sub (fan-out) demo.

One publish → every worker on the same topic gets a copy.

Run from the repo root:

    PYTHONPATH=src python examples/pubsub_demo.py
"""

from __future__ import annotations

import asyncio

from command_bus import CommandBusRouter, EventBus, EventMessage
from command_bus.adapters import InMemoryPubSubAdapter


TOPIC = "order-events"


class OrderCreated(EventMessage):
    order_id: str
    amount_cents: int


def make_worker(name: str) -> EventBus:
    """Each worker needs its own adapter instance on the same topic."""
    from command_bus import CommandHandler

    router = CommandBusRouter()

    class Handler(CommandHandler):
        def process(self, message: EventMessage) -> None:
            assert isinstance(message, OrderCreated)
            print(
                f"  [{name}] got order_id={message.order_id!r} "
                f"amount_cents={message.amount_cents}"
            )

    router.register(OrderCreated, Handler)
    adapter = InMemoryPubSubAdapter(queue_name=TOPIC)
    return EventBus(queue_adapter=adapter, command_router=router)


async def main() -> None:
    print(f"Starting 3 workers on topic {TOPIC!r}...\n")
    workers = [make_worker("worker-A"), make_worker("worker-B"), make_worker("worker-C")]

    # Publisher does not need local handlers
    publisher = EventBus(queue_adapter=InMemoryPubSubAdapter(queue_name=TOPIC))

    print("Publishing one event...")
    await publisher.publish(OrderCreated(order_id="ord-42", amount_cents=1999))
    print("Done. Each worker now polls once:\n")

    for w in workers:
        await w.work()

    print("\nAll three workers received the same event (fan-out).")


if __name__ == "__main__":
    asyncio.run(main())
