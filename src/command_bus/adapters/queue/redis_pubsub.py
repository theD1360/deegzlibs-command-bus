"""Redis Pub/Sub fan-out adapter."""

from collections import deque
from threading import Lock, Thread
from typing import Any, Deque, List, Optional

from ...interfaces import CommandBusAdapter, TransmissibleBaseModel


class _RedisPubSubMessage:
    """Wrapper so Redis pub/sub messages have .body and .delete()."""

    __slots__ = ("body",)

    def __init__(self, body: str) -> None:
        self.body = body

    def delete(self) -> None:
        """No-op: pub/sub messages are not acked."""
        pass


class RedisPubSubAdapter(CommandBusAdapter):
    """
    Fan-out adapter using Redis PUBLISH / SUBSCRIBE.

    ``enqueue`` publishes to ``queue_name`` (channel). Each adapter instance
    subscribes and buffers inbound messages for ``get_messages``.
    """

    def __init__(self, redis_client: Any, queue_name: str) -> None:
        self._redis = redis_client
        self.queue_name = queue_name
        self._buffer: Deque[str] = deque()
        self._buffer_lock = Lock()
        self._pubsub: Optional[Any] = None
        self._listener_thread: Optional[Thread] = None
        self._stopped = False
        self._ensure_subscribed()

    def _ensure_subscribed(self) -> None:
        if self._pubsub is not None:
            return
        self._pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
        self._pubsub.subscribe(self.queue_name)
        self._listener_thread = Thread(
            target=self._listen_loop,
            name=f"redis-pubsub-{self.queue_name}",
            daemon=True,
        )
        self._listener_thread.start()

    def _listen_loop(self) -> None:
        assert self._pubsub is not None
        while not self._stopped:
            try:
                msg = self._pubsub.get_message(timeout=0.2)
            except Exception:
                if self._stopped:
                    break
                continue
            if msg is None:
                continue
            if msg.get("type") != "message":
                continue
            data = msg.get("data")
            if data is None:
                continue
            body = data.decode("utf-8") if isinstance(data, bytes) else str(data)
            with self._buffer_lock:
                self._buffer.append(body)

    def enqueue(
        self,
        message_instance: TransmissibleBaseModel,
        delay_seconds: int = 0,
    ) -> None:
        """PUBLISH to the channel. delay_seconds is ignored."""
        self._redis.publish(self.queue_name, str(message_instance))

    def dequeue(self, message_instance: Any) -> None:
        if hasattr(message_instance, "delete"):
            message_instance.delete()

    def get_messages(
        self,
        max_messages: int = 1,
        wait_seconds: int = 0,
        **kwargs: Any,
    ) -> List[_RedisPubSubMessage]:
        """Drain up to max_messages from the local subscription buffer."""
        out: List[_RedisPubSubMessage] = []
        with self._buffer_lock:
            for _ in range(max_messages):
                try:
                    body = self._buffer.popleft()
                except IndexError:
                    break
                out.append(_RedisPubSubMessage(body=body))
        return out

    def close(self) -> None:
        """Stop the listener and unsubscribe."""
        self._stopped = True
        if self._pubsub is not None:
            try:
                self._pubsub.unsubscribe(self.queue_name)
                self._pubsub.close()
            except Exception:
                pass
            self._pubsub = None
        if self._listener_thread is not None and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=2.0)
        self._listener_thread = None
