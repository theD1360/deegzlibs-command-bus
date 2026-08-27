"""Tests for SNS Pub/Sub adapter (mocked)."""

import json

import pytest
from unittest.mock import MagicMock

from command_bus import EventMessage, EventBus, CommandBusRouter, MessageParserBase
from command_bus.adapters.queue.sns_pubsub import (
    SnsPubSubAdapter,
    _SnsPubSubMessage,
    _unwrap_sns_message,
)


class DummyEvent(EventMessage):
    id: str


class EnvelopeEvent(EventMessage):
    event_type: str
    payload: dict


class TsgStyleParser(MessageParserBase):
    def __init__(self, message_string: str) -> None:
        self._raw = message_string

    def initialize(self) -> EnvelopeEvent:
        data = json.loads(self._raw)
        return EnvelopeEvent(
            event_type=data["header"]["eventType"],
            payload=data["data"],
        )

    @classmethod
    def dumps(cls, message: EnvelopeEvent) -> str:
        return json.dumps(
            {
                "header": {
                    "eventType": message.event_type,
                    "eventTrace": ["QUAL_ENGINE"],
                    "traceId": "trace-1",
                    "spanId": "span-1",
                },
                "data": message.payload,
            }
        )

    @classmethod
    def subject(cls, message: EnvelopeEvent, encoded_body: str) -> str:
        return message.event_type

    @classmethod
    def message_attributes(cls, message: EnvelopeEvent, encoded_body: str):
        return {
            "eventType": {
                "DataType": "String",
                "StringValue": message.event_type,
            },
        }


def test_unwrap_sns_message_extracts_payload():
    envelope = {
        "Type": "Notification",
        "MessageId": "mid",
        "TopicArn": "arn:aws:sns:us-east-1:123:events",
        "Message": "actual-payload",
    }
    assert _unwrap_sns_message(json.dumps(envelope)) == "actual-payload"


def test_unwrap_sns_message_returns_raw_when_not_envelope():
    assert _unwrap_sns_message("plain-body") == "plain-body"
    assert _unwrap_sns_message("{not-json") == "{not-json"


def test_sns_pubsub_message_wrapper():
    sqs_msg = MagicMock()
    msg = _SnsPubSubMessage(body="hello", sqs_message=sqs_msg)
    assert msg.body == "hello"
    msg.delete()
    sqs_msg.delete.assert_called_once()


def test_sns_pubsub_adapter_enqueue_with_parser_hooks():
    sns_client = MagicMock()
    adapter = SnsPubSubAdapter(
        topic_arn="arn:aws:sns:us-east-1:123:order-events",
        sns_client=sns_client,
        message_parser_class=TsgStyleParser,
    )

    event = EnvelopeEvent(
        event_type="OFFER_GENERATED",
        payload={"accountUuid": "acct-1"},
    )
    adapter.enqueue(event)

    sns_client.publish.assert_called_once()
    call = sns_client.publish.call_args
    assert call.kwargs["TopicArn"] == "arn:aws:sns:us-east-1:123:order-events"
    assert call.kwargs["Subject"] == "OFFER_GENERATED"
    assert call.kwargs["MessageAttributes"]["eventType"]["StringValue"] == "OFFER_GENERATED"
    body = json.loads(call.kwargs["Message"])
    assert body["header"]["eventType"] == "OFFER_GENERATED"
    assert body["data"]["accountUuid"] == "acct-1"


def test_sns_pubsub_adapter_publish_only_get_messages_raises():
    sns_client = MagicMock()
    adapter = SnsPubSubAdapter(
        topic_arn="arn:aws:sns:us-east-1:123:events",
        sns_client=sns_client,
    )

    with pytest.raises(RuntimeError, match="sqs_client and queue_url"):
        adapter.get_messages()


def test_event_bus_binds_parser_on_sns_adapter():
    sns_client = MagicMock()
    sqs_client = MagicMock()
    sqs_client.Queue.return_value = MagicMock()

    adapter = SnsPubSubAdapter(
        topic_arn="arn:aws:sns:us-east-1:123:events",
        sns_client=sns_client,
        sqs_client=sqs_client,
        queue_url="https://sqs.us-east-1.amazonaws.com/123/worker-a",
    )
    assert adapter.message_parser_class is None

    EventBus(
        queue_adapter=adapter,
        command_router=CommandBusRouter(),
        message_parser_class=TsgStyleParser,
    )
    assert adapter.message_parser_class is TsgStyleParser


def test_sns_pubsub_adapter_enqueue_with_sns_client():
    sns_client = MagicMock()
    sqs_client = MagicMock()
    sqs_queue = MagicMock()
    sqs_client.Queue.return_value = sqs_queue

    adapter = SnsPubSubAdapter(
        topic_arn="arn:aws:sns:us-east-1:123:order-events",
        sns_client=sns_client,
        sqs_client=sqs_client,
        queue_url="https://sqs.us-east-1.amazonaws.com/123/worker-a",
    )

    event = DummyEvent(id="x")
    adapter.enqueue(event)

    sns_client.publish.assert_called_once_with(
        TopicArn="arn:aws:sns:us-east-1:123:order-events",
        Message=str(event),
    )


def test_sns_pubsub_adapter_enqueue_with_topic_resource():
    topic = MagicMock()
    topic.topic_arn = "arn:aws:sns:us-east-1:123:order-events"
    sqs_client = MagicMock()
    sqs_client.Queue.return_value = MagicMock()

    adapter = SnsPubSubAdapter(
        topic_arn=topic.topic_arn,
        sns_client=topic,
        sqs_client=sqs_client,
        queue_url="https://sqs.us-east-1.amazonaws.com/123/worker-a",
    )

    event = DummyEvent(id="y")
    adapter.enqueue(event)

    topic.publish.assert_called_once_with(Message=str(event))


def test_sns_pubsub_adapter_get_messages_unwraps_sns_envelope():
    sns_client = MagicMock()
    sqs_client = MagicMock()
    sqs_queue = MagicMock()
    sqs_client.Queue.return_value = sqs_queue

    sqs_msg = MagicMock()
    sqs_msg.body = json.dumps(
        {
            "Type": "Notification",
            "Message": "module.DummyEvent(id='z')",
        }
    )
    sqs_queue.receive_messages.return_value = [sqs_msg]

    adapter = SnsPubSubAdapter(
        topic_arn="arn:aws:sns:us-east-1:123:events",
        sns_client=sns_client,
        sqs_client=sqs_client,
        queue_url="https://sqs.us-east-1.amazonaws.com/123/worker-a",
    )

    messages = adapter.get_messages(max_messages=1, wait_seconds=5)
    assert len(messages) == 1
    assert messages[0].body == "module.DummyEvent(id='z')"
    sqs_queue.receive_messages.assert_called_once_with(
        MessageAttributeNames=["ALL"],
        MaxNumberOfMessages=1,
        WaitTimeSeconds=5,
        VisibilityTimeout=60,
    )


def test_sns_pubsub_adapter_dequeue():
    sns_client = MagicMock()
    sqs_client = MagicMock()
    sqs_client.Queue.return_value = MagicMock()

    adapter = SnsPubSubAdapter(
        topic_arn="arn:aws:sns:us-east-1:123:events",
        sns_client=sns_client,
        sqs_client=sqs_client,
        queue_url="https://sqs.us-east-1.amazonaws.com/123/worker-a",
    )

    message_handle = MagicMock()
    adapter.dequeue(message_handle)
    message_handle.delete.assert_called_once()
