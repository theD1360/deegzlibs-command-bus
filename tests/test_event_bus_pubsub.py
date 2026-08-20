"""Tests for in-memory pub/sub adapter and EventBus fan-out."""

import pytest
from command_bus import EventBus, EventMessage, CommandBusRouter, CommandHandler
from command_bus.adapters import InMemoryPubSubAdapter
from command_bus.adapters.queue.in_memory_pubsub import _reset_in_memory_pubsub_broker


class DummyEvent(EventMessage):
    id: str


class OrderCreated(EventMessage):
    order_id: str


@pytest.fixture(autouse=True)
def _clean_broker():
    _reset_in_memory_pubsub_broker()
    yield
    _reset_in_memory_pubsub_broker()


def test_in_memory_pubsub_fanout_to_two_subscribers():
    sub_a = InMemoryPubSubAdapter(queue_name="orders")
    sub_b = InMemoryPubSubAdapter(queue_name="orders")
    publisher = InMemoryPubSubAdapter(queue_name="orders")

    publisher.enqueue(DummyEvent(id="e1"))

    msgs_a = sub_a.get_messages(max_messages=5)
    msgs_b = sub_b.get_messages(max_messages=5)
    assert len(msgs_a) == 1
    assert len(msgs_b) == 1
    assert "e1" in msgs_a[0].body
    assert "e1" in msgs_b[0].body


def test_in_memory_pubsub_isolated_topics():
    a = InMemoryPubSubAdapter(queue_name="a")
    b = InMemoryPubSubAdapter(queue_name="b")
    a.enqueue(DummyEvent(id="only-a"))
    assert len(a.get_messages()) == 1
    assert len(b.get_messages()) == 0


@pytest.mark.asyncio
async def test_event_bus_publish_without_local_handler():
    adapter = InMemoryPubSubAdapter(queue_name="events")
    bus = EventBus(queue_adapter=adapter, command_router=CommandBusRouter())
    await bus.publish(DummyEvent(id="x"))
    msgs = adapter.get_messages()
    assert len(msgs) == 1


@pytest.mark.asyncio
async def test_event_bus_publish_and_work_multiple_workers():
    topic = "fanout-test"
    worker_a_adapter = InMemoryPubSubAdapter(queue_name=topic)
    worker_b_adapter = InMemoryPubSubAdapter(queue_name=topic)
    publisher_adapter = InMemoryPubSubAdapter(queue_name=topic)

    received_a: list = []
    received_b: list = []

    router_a = CommandBusRouter()
    router_b = CommandBusRouter()

    class HandlerA(CommandHandler):
        def process(self, message):
            received_a.append(message.order_id)

    class HandlerB(CommandHandler):
        def process(self, message):
            received_b.append(message.order_id)

    router_a.register(OrderCreated, HandlerA)
    router_b.register(OrderCreated, HandlerB)

    bus_a = EventBus(queue_adapter=worker_a_adapter, command_router=router_a)
    bus_b = EventBus(queue_adapter=worker_b_adapter, command_router=router_b)
    publisher = EventBus(queue_adapter=publisher_adapter)

    await publisher.publish(OrderCreated(order_id="ord-99"))
    await bus_a.work()
    await bus_b.work()

    assert received_a == ["ord-99"]
    assert received_b == ["ord-99"]


@pytest.mark.asyncio
async def test_router_event_decorator_publish_and_work():
    adapter = InMemoryPubSubAdapter(queue_name="decorated")
    router = CommandBusRouter()
    bus = EventBus(queue_adapter=adapter, command_router=router)
    received: list[str] = []

    @router.event()
    def on_ping(name: str):
        received.append(name)

    await bus.publish(on_ping(name="hello"))
    await bus.work()
    assert received == ["hello"]
    assert issubclass(on_ping._command_message_class, EventMessage)


@pytest.mark.asyncio
async def test_event_bus_dispatch_no_handler_is_noop():
    adapter = InMemoryPubSubAdapter(queue_name="noop")
    bus = EventBus(queue_adapter=adapter)
    await bus.publish(DummyEvent(id="z"))
    await bus.work()  # no handlers registered — should not raise
