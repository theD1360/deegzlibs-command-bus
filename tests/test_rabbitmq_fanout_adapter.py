"""Tests for RabbitMQ fanout adapter (mocked)."""

import pytest

pytest.importorskip("pika")

from unittest.mock import MagicMock, patch

from command_bus import EventMessage
from command_bus.adapters.queue.rabbitmq_fanout import (
    RabbitMqFanoutAdapter,
    _RabbitMQFanoutMessage,
)


class DummyEvent(EventMessage):
    id: str


def test_rabbitmq_fanout_requires_connection():
    with pytest.raises(ValueError, match="connection_url or connection_params"):
        RabbitMqFanoutAdapter(queue_name="events")


def test_rabbitmq_fanout_message_delete_acks():
    channel = MagicMock()
    msg = _RabbitMQFanoutMessage(body="{}", channel=channel, delivery_tag=3)
    msg.delete()
    channel.basic_ack.assert_called_once_with(3)


@patch("command_bus.adapters.queue.rabbitmq_fanout.pika")
def test_rabbitmq_fanout_enqueue(pika_mock):
    conn = MagicMock()
    ch = MagicMock()
    pika_mock.BlockingConnection.return_value = conn
    conn.channel.return_value = ch

    adapter = RabbitMqFanoutAdapter(
        queue_name="order-events",
        connection_url="amqp://localhost/",
    )
    msg = DummyEvent(id="x")
    adapter.enqueue(msg)

    ch.exchange_declare.assert_called_once()
    call_kw = ch.exchange_declare.call_args[1]
    assert call_kw["exchange"] == "order-events"
    assert call_kw["exchange_type"] == "fanout"

    ch.basic_publish.assert_called_once()
    pub_kw = ch.basic_publish.call_args[1]
    assert pub_kw["exchange"] == "order-events"
    assert pub_kw["routing_key"] == ""
    conn.close.assert_called_once()


@patch("command_bus.adapters.queue.rabbitmq_fanout.pika")
def test_rabbitmq_fanout_get_messages(pika_mock):
    conn = MagicMock()
    ch = MagicMock()
    pika_mock.BlockingConnection.return_value = conn
    conn.channel.return_value = ch
    conn.is_open = True
    ch.is_closed = False

    result = MagicMock()
    result.method.queue = "amq.gen-exclusive"
    ch.queue_declare.return_value = result

    method = MagicMock()
    method.delivery_tag = 1
    ch.basic_get.side_effect = [(method, None, b"body-1"), (None, None, None)]

    adapter = RabbitMqFanoutAdapter(
        queue_name="ev",
        connection_url="amqp://localhost/",
    )
    messages = adapter.get_messages(max_messages=2)
    assert len(messages) == 1
    assert messages[0].body == "body-1"
    ch.queue_bind.assert_called_once()
    adapter.close()
