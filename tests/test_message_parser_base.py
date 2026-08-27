"""Tests for MessageParserBase outbound and SNS hooks."""

import json

from command_bus import CommandMessage, EventMessage, MessageParserBase


class SampleCommand(CommandMessage):
    id: str


class SampleEvent(EventMessage):
    name: str


class EnvelopeMessage(EventMessage):
    event_type: str
    payload: dict


class TsgStyleParser(MessageParserBase):
    """Example parser qual-e could mirror for TSG SNS envelopes."""

    def __init__(self, message_string: str) -> None:
        self._raw = message_string

    def initialize(self) -> EnvelopeMessage:
        data = json.loads(self._raw)
        header = data["header"]
        return EnvelopeMessage(
            event_type=header["eventType"],
            payload=data["data"],
        )

    @classmethod
    def dumps(cls, message: EnvelopeMessage) -> str:
        envelope = {
            "header": {
                "eventType": message.event_type,
                "eventTrace": ["QUAL_ENGINE"],
                "traceId": "abc123",
                "spanId": "def456",
            },
            "data": message.payload,
        }
        return json.dumps(envelope)

    @classmethod
    def subject(cls, message: EnvelopeMessage, encoded_body: str) -> str:
        return message.event_type

    @classmethod
    def message_attributes(
        cls,
        message: EnvelopeMessage,
        encoded_body: str,
    ):
        return {
            "eventType": {
                "DataType": "String",
                "StringValue": message.event_type,
            },
        }


def test_base_dumps_defaults_to_str():
    msg = SampleCommand(id="x")
    assert MessageParserBase.dumps(msg) == str(msg)


def test_base_sns_hooks_default_to_none():
    msg = SampleEvent(name="ping")
    assert MessageParserBase.subject(msg, "body") is None
    assert MessageParserBase.message_attributes(msg, "body") is None


def test_tsg_style_parser_round_trip():
    original = EnvelopeMessage(
        event_type="OFFER_GENERATED",
        payload={"accountUuid": "acct-1", "offerCount": 3},
    )
    encoded = TsgStyleParser.dumps(original)
    parsed = TsgStyleParser(encoded).initialize()

    assert parsed.event_type == "OFFER_GENERATED"
    assert parsed.payload["accountUuid"] == "acct-1"


def test_tsg_style_parser_sns_hooks():
    msg = EnvelopeMessage(event_type="OFFER_GENERATED", payload={})
    body = TsgStyleParser.dumps(msg)

    assert TsgStyleParser.subject(msg, body) == "OFFER_GENERATED"
    attrs = TsgStyleParser.message_attributes(msg, body)
    assert attrs["eventType"]["StringValue"] == "OFFER_GENERATED"
