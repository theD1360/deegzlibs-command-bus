"""Tests for Redis queue adapter (mocked)."""

from unittest.mock import MagicMock

import pytest
from command_bus import CommandBus, CommandBusRouter, CommandMessage
from command_bus.adapters.queue.redis import RedisCommandBusAdapter, _RedisMessage


class DummyMessage(CommandMessage):
    id: str


def test_redis_message_wrapper():
    m = _RedisMessage(body="hello")
    assert m.body == "hello"
    m.delete()  # no-op, no error


def test_redis_adapter_enqueue():
    redis_mock = MagicMock()
    adapter = RedisCommandBusAdapter(redis_client=redis_mock, queue_name="myqueue")
    msg = DummyMessage(id="x")
    adapter.enqueue(msg, delay_seconds=0)
    redis_mock.lpush.assert_called_once_with("myqueue", str(msg))
    assert "x" in redis_mock.lpush.call_args[0][1]


def test_redis_adapter_get_messages_nonblocking():
    redis_mock = MagicMock()
    redis_mock.rpop.side_effect = [b"msg1", None]
    adapter = RedisCommandBusAdapter(redis_client=redis_mock, queue_name="q")
    messages = adapter.get_messages(max_messages=2, wait_seconds=0)
    assert len(messages) == 1
    assert messages[0].body == "msg1"
    assert redis_mock.rpop.call_count == 2


def test_redis_adapter_get_messages_blocking():
    redis_mock = MagicMock()
    redis_mock.brpop.return_value = ("q", b"payload")
    adapter = RedisCommandBusAdapter(redis_client=redis_mock, queue_name="q")
    messages = adapter.get_messages(max_messages=1, wait_seconds=5)
    assert len(messages) == 1
    assert messages[0].body == "payload"
    redis_mock.brpop.assert_called_once_with("q", timeout=5)


@pytest.mark.asyncio
async def test_redis_command_bus_execute_and_work():
    redis_mock = MagicMock()
    redis_mock.brpop.return_value = None
    redis_mock.rpop.return_value = None
    adapter = RedisCommandBusAdapter(redis_client=redis_mock, queue_name="events")
    registry = CommandBusRouter()

    class Handler:
        def process(self, message):
            pass

    registry.register(DummyMessage, Handler)
    bus = CommandBus(queue_adapter=adapter, command_router=registry)
    await bus.execute(DummyMessage(id="a"), wait=False)
    redis_mock.lpush.assert_called_once()
    assert "a" in redis_mock.lpush.call_args[0][1]
