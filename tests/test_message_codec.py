"""Tests for MessageCodec and JsonMessageParser codec integration."""

import json

import pytest
from command_bus import CommandMessage, JsonMessageParser
from command_bus.parsers.codec import (
    Base64MessageCodec,
    ChainedMessageCodec,
    GzipMessageCodec,
    IdentityMessageCodec,
    configure_json_parser,
)


class OrderCreated(CommandMessage):
    order_id: str
    amount_cents: int


def test_identity_codec_round_trip():
    codec = IdentityMessageCodec()
    assert codec.decode(codec.encode("payload")) == "payload"


def test_base64_codec_round_trip():
    codec = Base64MessageCodec()
    assert codec.decode(codec.encode('{"x": 1}')) == '{"x": 1}'


def test_gzip_codec_round_trip():
    codec = GzipMessageCodec()
    payload = '{"order_id": "ord-1", "amount_cents": 100}'
    assert codec.decode(codec.encode(payload)) == payload


def test_chained_codec_encode_decode_order():
    codec = ChainedMessageCodec([GzipMessageCodec(), Base64MessageCodec()])
    payload = '{"__type__": "tests.test_message_codec.OrderCreated", "order_id": "a"}'
    wrapped = codec.encode(payload)
    assert wrapped != payload
    assert codec.decode(wrapped) == payload


def test_json_parser_with_base64_codec():
    msg = OrderCreated(order_id="ord-123", amount_cents=1999)
    codec = Base64MessageCodec()
    wrapped = JsonMessageParser.dumps(msg, codec=codec)

    parser = JsonMessageParser(wrapped, codec=codec)
    parsed = parser.initialize()
    assert isinstance(parsed, OrderCreated)
    assert parsed.order_id == "ord-123"
    assert parsed.amount_cents == 1999


def test_json_parser_with_chained_gzip_base64_codec():
    msg = OrderCreated(order_id="ord-456", amount_cents=500)
    codec = ChainedMessageCodec([GzipMessageCodec(), Base64MessageCodec()])
    wrapped = JsonMessageParser.dumps(msg, codec=codec)

    parser = JsonMessageParser(wrapped, codec=codec)
    parsed = parser.initialize()
    assert parsed.order_id == "ord-456"
    assert parsed.amount_cents == 500


def test_json_parser_dumps_without_codec():
    msg = OrderCreated(order_id="plain", amount_cents=1)
    raw = JsonMessageParser.dumps(msg)
    payload = json.loads(raw)
    assert payload["__type__"] == "tests.test_message_codec.OrderCreated"
    assert payload["order_id"] == "plain"


def test_configure_json_parser_factory():
    codec = Base64MessageCodec()
    parser_class = configure_json_parser(codec=codec, type_key="type")
    msg = OrderCreated(order_id="factory", amount_cents=42)
    wrapped = JsonMessageParser.dumps(msg, type_key="type", codec=codec)

    parser = parser_class(wrapped)
    parsed = parser.initialize()
    assert parsed.order_id == "factory"


@pytest.mark.asyncio
async def test_command_bus_with_configured_json_parser():
    from unittest.mock import MagicMock

    from command_bus import CommandBus, CommandBusRouter, CommandHandler

    codec = Base64MessageCodec()
    parser_class = configure_json_parser(codec=codec)
    adapter = MagicMock()
    adapter.get_messages.return_value = []

    router = CommandBusRouter()

    class OrderHandler(CommandHandler):
        def process(self, message):
            return message.order_id

    router.register(OrderCreated, OrderHandler)
    bus = CommandBus(
        queue_adapter=adapter,
        command_router=router,
        message_parser_class=parser_class,
    )

    wrapped = JsonMessageParser.dumps(
        OrderCreated(order_id="bus-test", amount_cents=100),
        codec=codec,
    )
    result = await bus.dispatch(wrapped)
    assert result is None

    adapter = MagicMock()
    message = MagicMock()
    message.body = wrapped
    adapter.get_messages.return_value = [message]
    bus = CommandBus(
        queue_adapter=adapter,
        command_router=router,
        message_parser_class=parser_class,
    )
    await bus.work()
    adapter.dequeue.assert_called_once_with(message)
