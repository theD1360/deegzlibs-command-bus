#!/usr/bin/env python3
"""
Encode a Qual-Engine TSG SNS envelope using command_bus MessageCodec.

Qual-Engine publishes events like OFFER_GENERATED to SNS with this body shape
(see qual-engine/app/lib/notifications/interfaces/sns_message.py):

    {
      "header": {
        "eventType": "OFFER_GENERATED",
        "eventTrace": ["QUAL_ENGINE"],
        "traceId": "<32-char hex>",
        "spanId": "<16-char hex>"
      },
      "data": { ... camelCase event fields ... }
    }

Header fields are also duplicated as SNS MessageAttributes; eventType is the
SNS Subject. This script builds that envelope locally, validates/serializes it
with TsgEnvelopeCodec (a MessageCodec), and shows the boto3 publish call Qual-E
would make.

Run from the repo root:

    PYTHONPATH=src python examples/qual_e_tsg_sns_envelope.py

Optional — print only the encoded SNS Message body:

    PYTHONPATH=src python examples/qual_e_tsg_sns_envelope.py --message-only
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

from pydantic import BaseModel, Field

from command_bus.parsers.codec import ChainedMessageCodec, GzipMessageCodec, MessageCodec


# ---------------------------------------------------------------------------
# TSG envelope models (mirrors qual-engine SNSMessage / QualEngineEvent)
# ---------------------------------------------------------------------------


class SNSMessageHeader(BaseModel):
    """TSG standard SNS message header."""

    eventType: str
    eventTrace: list[str]
    traceId: str
    spanId: str


class SNSMessage(BaseModel):
    """TSG standard SNS message: header + camelCase data."""

    header: SNSMessageHeader
    data: dict[str, Any] = Field(..., description="Event-specific data in camelCase")


def create_offer_generated_event(
    *,
    offers_response: dict[str, Any],
    account_uuid: str | None = None,
    user_uuid: str | None = None,
    processing_time_ms: int | None = None,
    event_trace: list[str] | None = None,
    trace_id: str = "d61574b993403f4e9bf9b5a10e53c409",
    span_id: str = "315d990c35609f75",
) -> SNSMessage:
    """
    Build OFFER_GENERATED the same way qual-engine does in
    app/src/notifications/events/offer_generated.py.
    """
    data = {
        "offersResponse": offers_response,
        "accountUuid": account_uuid,
        "userUuid": user_uuid,
        "processingTimeMs": processing_time_ms,
        "timestamp": datetime.utcnow().isoformat(),
    }
    data = {key: value for key, value in data.items() if value is not None}

    return SNSMessage(
        header=SNSMessageHeader(
            eventType="OFFER_GENERATED",
            eventTrace=event_trace or ["QUAL_ENGINE"],
            traceId=trace_id,
            spanId=span_id,
        ),
        data=data,
    )


def sample_offers_response() -> dict[str, Any]:
    """Minimal offersResponse payload matching qual-engine tests."""
    return {
        "uuid": "123e4567-e89b-12d3-a456-426614174000",
        "metadata": {
            "modifiers": {"approvalCutoff": 0.5},
            "terms": [24, 36, 48, 60, 72, 84, 96, 120],
            "rates": {"min": "0.0559", "mean": "0.0761", "max": "0.1301"},
            "createdAt": "2025-10-03T17:40:27.037605",
        },
        "lenderOffers": [
            {"lenderName": "Test Lender 1", "approved": True, "rate": "0.0659"},
            {"lenderName": "Test Lender 2", "approved": True, "rate": "0.0759"},
        ],
        "offersPerTermBand": [{"term": 60, "offers": []}],
        "message": "Offers generated successfully",
    }


# ---------------------------------------------------------------------------
# TSG envelope codec (MessageCodec wrapper around qual-e JSON body)
# ---------------------------------------------------------------------------


class TsgEnvelopeCodec(MessageCodec):
    """
    Validate and serialize TSG SNS envelope JSON.

    encode: SNSMessage -> JSON string (validated)
    decode: JSON string -> JSON string (validated, for downstream parsers)
    """

    REQUIRED_HEADER_FIELDS = ("eventType", "eventTrace", "traceId", "spanId")

    @classmethod
    def validate_structure(cls, message_data: dict[str, Any]) -> None:
        if not isinstance(message_data, dict):
            raise ValueError("TSG envelope must be a JSON object")
        if "header" not in message_data or "data" not in message_data:
            raise ValueError("TSG envelope must contain 'header' and 'data'")

        header = message_data["header"]
        data = message_data["data"]

        if not isinstance(header, dict):
            raise ValueError("TSG envelope 'header' must be an object")
        if not isinstance(data, dict):
            raise ValueError("TSG envelope 'data' must be an object")

        for field in cls.REQUIRED_HEADER_FIELDS:
            if field not in header:
                raise ValueError(f"TSG header missing required field: {field}")
        if not isinstance(header["eventTrace"], list):
            raise ValueError("TSG header 'eventTrace' must be a list")

    @classmethod
    def from_message(cls, message: SNSMessage) -> str:
        payload = message.model_dump()
        cls.validate_structure(payload)
        return json.dumps(payload, separators=(",", ":"))

    @classmethod
    def to_message(cls, envelope_json: str) -> SNSMessage:
        data = json.loads(envelope_json)
        cls.validate_structure(data)
        return SNSMessage.model_validate(data)

    def encode(self, payload: str) -> str:
        parsed = json.loads(payload)
        self.validate_structure(parsed)
        return json.dumps(parsed, separators=(",", ":"))

    def decode(self, wrapped: str) -> str:
        parsed = json.loads(wrapped)
        self.validate_structure(parsed)
        return json.dumps(parsed, separators=(",", ":"))


def extract_sns_message_attributes(message: SNSMessage) -> dict[str, dict[str, str]]:
    """
    Same attribute mapping as qual-engine JsonSNSMessageEncoder.extract_message_attributes.
    """
    return {
        "eventType": {
            "DataType": "String",
            "StringValue": message.header.eventType,
        },
        "eventTrace": {
            "DataType": "String",
            "StringValue": ",".join(message.header.eventTrace),
        },
        "traceId": {
            "DataType": "String",
            "StringValue": message.header.traceId,
        },
        "spanId": {
            "DataType": "String",
            "StringValue": message.header.spanId,
        },
    }


def build_sns_publish_request(
    message: SNSMessage,
    topic_arn: str,
    *,
    transport_codec: MessageCodec | None = None,
) -> dict[str, Any]:
    """
    Build kwargs for boto3 sns_client.publish(), matching qual-engine SnsNotificationAdapter.
    """
    codec = transport_codec or TsgEnvelopeCodec()
    inner_json = TsgEnvelopeCodec.from_message(message)
    encoded_message = codec.encode(inner_json)

    return {
        "TopicArn": topic_arn,
        "Message": encoded_message,
        "Subject": message.header.eventType,
        "MessageAttributes": extract_sns_message_attributes(message),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--message-only",
        action="store_true",
        help="Print only the encoded SNS Message body JSON",
    )
    args = parser.parse_args()

    event = create_offer_generated_event(
        offers_response=sample_offers_response(),
        account_uuid="account-123",
        user_uuid="user-456",
        processing_time_ms=1250,
    )

    topic_arn = "arn:aws:sns:us-east-1:123456789012:qual-engine-events-dev"
    tsg_codec = TsgEnvelopeCodec()

    # Plain TSG envelope JSON (what qual-engine puts in SNS Message by default)
    envelope_json = tsg_codec.encode(TsgEnvelopeCodec.from_message(event))

    if args.message_only:
        print(envelope_json)
        return

    print("=== Qual-Engine OFFER_GENERATED (Pydantic) ===")
    print(json.dumps(event.model_dump(), indent=2))

    print("\n=== TsgEnvelopeCodec.encode() -> SNS Message body ===")
    print(json.dumps(json.loads(envelope_json), indent=2))

    # Optional transport wrapper (e.g. gzip for large offersResponse payloads)
    transport_codec = ChainedMessageCodec([TsgEnvelopeCodec(), GzipMessageCodec()])
    compressed_body = transport_codec.encode(envelope_json)
    round_trip = transport_codec.decode(compressed_body)
    assert round_trip == envelope_json

    print("\n=== Optional transport codec (TSG validate + gzip) ===")
    print(f"Original size: {len(envelope_json)} bytes")
    print(f"Compressed size: {len(compressed_body)} bytes")
    print("(Consumers must use the same ChainedMessageCodec to unwrap before parsing.)")

    publish_request = build_sns_publish_request(event, topic_arn)

    print("\n=== boto3 sns.publish() request (qual-engine shape) ===")
    print(json.dumps(
        {
            "TopicArn": publish_request["TopicArn"],
            "Subject": publish_request["Subject"],
            "MessageAttributes": publish_request["MessageAttributes"],
            "Message": json.loads(publish_request["Message"]),
        },
        indent=2,
    ))

    # Mock publish — same flow as qual-engine/examples/sns_event_usage.py
    sns_client = MagicMock()
    sns_client.publish.return_value = {"MessageId": "mock-message-id-123"}
    sns_client.publish(**publish_request)

    print("\n=== Mock SNS publish succeeded ===")
    print(f"MessageId: {sns_client.publish.return_value['MessageId']}")

    decoded = TsgEnvelopeCodec.to_message(publish_request["Message"])
    print("\n=== Decode round-trip ===")
    print(f"eventType: {decoded.header.eventType}")
    print(f"accountUuid: {decoded.data.get('accountUuid')}")
    print(f"lenderOffers: {len(decoded.data['offersResponse']['lenderOffers'])}")


if __name__ == "__main__":
    main()
