"""Tests for Redis Pub/Sub adapter (mocked)."""

from unittest.mock import MagicMock, patch

import pytest
from command_bus import EventMessage
from command_bus.adapters.queue.redis_pubsub import RedisPubSubAdapter, _RedisPubSubMessage


class DummyEvent(EventMessage):
    id: str


def test_redis_pubsub_message_wrapper():
    m = _RedisPubSubMessage(body="hello")
    assert m.body == "hello"
    m.delete()


@patch("command_bus.adapters.queue.redis_pubsub.Thread")
def test_redis_pubsub_adapter_enqueue(thread_mock):
    redis_mock = MagicMock()
    pubsub = MagicMock()
    redis_mock.pubsub.return_value = pubsub

    adapter = RedisPubSubAdapter(redis_client=redis_mock, queue_name="chan")
    msg = DummyEvent(id="x")
    adapter.enqueue(msg)
    redis_mock.publish.assert_called_once_with("chan", str(msg))
    pubsub.subscribe.assert_called_once_with("chan")
    adapter.close()


@patch("command_bus.adapters.queue.redis_pubsub.Thread")
def test_redis_pubsub_get_messages_from_buffer(thread_mock):
    redis_mock = MagicMock()
    pubsub = MagicMock()
    redis_mock.pubsub.return_value = pubsub

    adapter = RedisPubSubAdapter(redis_client=redis_mock, queue_name="chan")
    with adapter._buffer_lock:
        adapter._buffer.append("payload-1")
        adapter._buffer.append("payload-2")

    messages = adapter.get_messages(max_messages=2)
    assert len(messages) == 2
    assert messages[0].body == "payload-1"
    assert messages[1].body == "payload-2"
    adapter.close()
