"""RabbitMQ fanout exchange adapter for pub/sub."""

from typing import Any, List, Optional

import pika
from pika.adapters.blocking_connection import BlockingChannel

from ...interfaces import QueueAdapter, TransmissibleBaseModel


class _RabbitMQFanoutMessage:
    """Wrapper so RabbitMQ fanout messages have .body and .delete()."""

    __slots__ = ("body", "_channel", "_delivery_tag")

    def __init__(self, body: str, channel: BlockingChannel, delivery_tag: int) -> None:
        self.body = body
        self._channel = channel
        self._delivery_tag = delivery_tag

    def delete(self) -> None:
        self._channel.basic_ack(self._delivery_tag)


class RabbitMqFanoutAdapter(QueueAdapter):
    """
    Fan-out adapter using a RabbitMQ fanout exchange named ``queue_name``.

    Producers publish to the exchange. Each consumer instance declares an exclusive
    auto-delete queue bound to the exchange, so every worker receives a copy.
    """

    def __init__(
        self,
        queue_name: str,
        connection_url: Optional[str] = None,
        connection_params: Optional[pika.ConnectionParameters] = None,
    ) -> None:
        if not connection_url and not connection_params:
            raise ValueError("Provide either connection_url or connection_params")
        self.queue_name = queue_name  # exchange / topic name
        self._connection_url = connection_url
        self._connection_params = connection_params
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[BlockingChannel] = None
        self._consumer_queue: Optional[str] = None

    def _open_connection(self) -> pika.BlockingConnection:
        if self._connection_url:
            return pika.BlockingConnection(pika.URLParameters(self._connection_url))
        return pika.BlockingConnection(self._connection_params)

    def _ensure_consumer(self) -> BlockingChannel:
        if self._channel is None or self._channel.is_closed:
            self._connection = self._open_connection()
            self._channel = self._connection.channel()
            self._channel.exchange_declare(
                exchange=self.queue_name,
                exchange_type="fanout",
                durable=True,
            )
            result = self._channel.queue_declare(queue="", exclusive=True, auto_delete=True)
            self._consumer_queue = result.method.queue
            self._channel.queue_bind(
                exchange=self.queue_name,
                queue=self._consumer_queue,
            )
        return self._channel

    def enqueue(
        self,
        message_instance: TransmissibleBaseModel,
        delay_seconds: int = 0,
    ) -> None:
        """Publish to the fanout exchange. delay_seconds is ignored."""
        conn = self._open_connection()
        try:
            ch = conn.channel()
            ch.exchange_declare(
                exchange=self.queue_name,
                exchange_type="fanout",
                durable=True,
            )
            ch.basic_publish(
                exchange=self.queue_name,
                routing_key="",
                body=str(message_instance),
                properties=pika.BasicProperties(delivery_mode=2),
            )
        finally:
            conn.close()

    def dequeue(self, message_instance: Any) -> None:
        if hasattr(message_instance, "delete"):
            message_instance.delete()
        else:
            raise TypeError(
                "message_instance must be a _RabbitMQFanoutMessage with .delete()"
            )

    def get_messages(
        self,
        max_messages: int = 1,
        **kwargs: Any,
    ) -> List[_RabbitMQFanoutMessage]:
        """Fetch messages from this worker's exclusive queue bound to the fanout exchange."""
        channel = self._ensure_consumer()
        assert self._consumer_queue is not None
        out: List[_RabbitMQFanoutMessage] = []
        for _ in range(max_messages):
            method_frame, _, body = channel.basic_get(queue=self._consumer_queue)
            if method_frame is None:
                break
            body_str = body.decode("utf-8") if isinstance(body, bytes) else body
            out.append(
                _RabbitMQFanoutMessage(
                    body=body_str,
                    channel=channel,
                    delivery_tag=method_frame.delivery_tag,
                )
            )
        return out

    def close(self) -> None:
        """Close the consumer connection."""
        if self._channel and not self._channel.is_closed:
            self._channel.close()
        if self._connection and self._connection.is_open:
            self._connection.close()
        self._channel = None
        self._connection = None
        self._consumer_queue = None
