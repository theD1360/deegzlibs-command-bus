"""Redis-backed queue adapter using Redis Streams + consumer groups."""

from __future__ import annotations

import os
import socket
import uuid
import warnings
from typing import Any, List, Optional

from ...interfaces import QueueAdapter, TransmissibleBaseModel

_BODY_FIELD = "body"
_DEFAULT_GROUP = "command-bus"


class _RedisMessage:
    """Wrapper so Redis messages have .body and .delete() like SQS/RabbitMQ."""

    __slots__ = ("body", "message_id", "_adapter")

    def __init__(self, body: str, message_id: str, adapter: "RedisQueueAdapter") -> None:
        self.body = body
        self.message_id = message_id
        self._adapter = adapter

    def delete(self) -> None:
        """Ack and remove the stream entry (XACK + XDEL)."""
        self._adapter._ack(self.message_id)


class RedisQueueAdapter(QueueAdapter):
    """
    Queue adapter using a Redis Stream with a consumer group.

    Requires Redis >= 6.2 (``XAUTOCLAIM`` for visibility-timeout reclaim).

    - ``enqueue`` → ``XADD``
    - ``get_messages`` → reclaim idle pending via ``XAUTOCLAIM``, then ``XREADGROUP``
    - ``dequeue`` / ``message.delete()`` → ``XACK`` + ``XDEL``

    Delivery is **at-least-once**: a crash before ack leaves the message in the
    pending entries list (PEL); after ``visibility_timeout`` seconds it can be
    claimed by another (or the same) consumer. Handlers must be idempotent.

    ``delay_seconds`` is not supported (no native delay on Streams).
    """

    def __init__(
        self,
        redis_client: Any,
        queue_name: str,
        *,
        consumer_group: str = _DEFAULT_GROUP,
        consumer_name: Optional[str] = None,
        default_visibility_timeout: int = 60,
    ) -> None:
        self._redis = redis_client
        self.queue_name = queue_name
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name or self._default_consumer_name()
        self.default_visibility_timeout = default_visibility_timeout
        self._group_ensured = False

    @staticmethod
    def _default_consumer_name() -> str:
        host = socket.gethostname().split(".")[0]
        return f"{host}:{os.getpid()}:{uuid.uuid4().hex[:8]}"

    def enqueue(
        self,
        message_instance: TransmissibleBaseModel,
        delay_seconds: int = 0,
    ) -> None:
        """Add a message to the stream. delay_seconds is ignored."""
        self._redis.xadd(self.queue_name, {_BODY_FIELD: str(message_instance)})

    def dequeue(self, message_instance: Any) -> None:
        """Ack and delete the stream entry."""
        if hasattr(message_instance, "delete"):
            message_instance.delete()

    def get_messages(
        self,
        max_messages: int = 1,
        wait_seconds: int = 0,
        visibility_timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> List[_RedisMessage]:
        """
        Fetch messages: reclaim idle pending first, then read new entries.

        ``visibility_timeout`` (seconds) maps to ``XAUTOCLAIM`` min-idle time.
        When omitted, uses ``default_visibility_timeout``.
        """
        if max_messages < 1:
            return []

        self._ensure_group()
        vis = (
            self.default_visibility_timeout
            if visibility_timeout is None
            else visibility_timeout
        )
        min_idle_ms = max(0, int(vis * 1000))
        out: List[_RedisMessage] = []

        claimed = self._autoclaim(min_idle_ms=min_idle_ms, count=max_messages)
        out.extend(claimed)

        remaining = max_messages - len(out)
        if remaining > 0:
            out.extend(
                self._read_group(
                    count=remaining,
                    wait_seconds=wait_seconds if not out else 0,
                )
            )
        return out

    def pending_message_count(self) -> int:
        """Return stream length (undelivered + still-pending after ack+delete policy)."""
        try:
            return int(self._redis.xlen(self.queue_name))
        except Exception:
            return 0

    def purge_messages(self) -> int:
        """Delete the stream key and return how many entries were removed."""
        count = self.pending_message_count()
        if count or self._redis.exists(self.queue_name):
            self._redis.delete(self.queue_name)
        self._group_ensured = False
        return count

    def _ensure_group(self) -> None:
        if self._group_ensured:
            return
        try:
            self._redis.xgroup_create(
                self.queue_name,
                self.consumer_group,
                id="0",
                mkstream=True,
            )
        except Exception as exc:
            # BUSYGROUP: group already exists — safe to continue
            if "BUSYGROUP" not in str(exc).upper():
                raise
        self._group_ensured = True

    def _ack(self, message_id: str) -> None:
        self._redis.xack(self.queue_name, self.consumer_group, message_id)
        self._redis.xdel(self.queue_name, message_id)

    def _parse_entries(self, entries: Any) -> List[_RedisMessage]:
        out: List[_RedisMessage] = []
        if not entries:
            return out
        for item in entries:
            message_id, fields = self._normalize_entry(item)
            if message_id is None:
                continue
            body = self._extract_body(fields)
            if body is None:
                continue
            out.append(_RedisMessage(body=body, message_id=message_id, adapter=self))
        return out

    def _autoclaim(self, *, min_idle_ms: int, count: int) -> List[_RedisMessage]:
        """Claim idle pending messages. Returns parsed messages."""
        try:
            result = self._redis.xautoclaim(
                name=self.queue_name,
                groupname=self.consumer_group,
                consumername=self.consumer_name,
                min_idle_time=min_idle_ms,
                start_id="0-0",
                count=count,
            )
        except Exception:
            return []

        # redis-py: (next_id, [(id, fields), ...], deleted_ids?) or similar
        entries = self._entries_from_autoclaim(result)
        return self._parse_entries(entries)

    def _read_group(self, *, count: int, wait_seconds: int) -> List[_RedisMessage]:
        block_ms: Optional[int]
        if wait_seconds and wait_seconds > 0:
            block_ms = int(wait_seconds * 1000)
        else:
            block_ms = None
        try:
            result = self._redis.xreadgroup(
                groupname=self.consumer_group,
                consumername=self.consumer_name,
                streams={self.queue_name: ">"},
                count=count,
                block=block_ms,
            )
        except Exception:
            return []
        if not result:
            return []
        # [(stream_name, [(id, fields), ...])]
        entries: list = []
        for _stream, msgs in result:
            entries.extend(msgs)
        return self._parse_entries(entries)

    @staticmethod
    def _entries_from_autoclaim(result: Any) -> list:
        if result is None:
            return []
        if isinstance(result, (list, tuple)):
            if len(result) >= 2 and isinstance(result[1], (list, tuple)):
                return list(result[1])
            # already a list of entries
            if result and isinstance(result[0], (list, tuple)) and len(result[0]) == 2:
                return list(result)
        return []

    @staticmethod
    def _normalize_entry(item: Any) -> tuple[Optional[str], Any]:
        if not item or not isinstance(item, (list, tuple)) or len(item) < 2:
            return None, None
        message_id, fields = item[0], item[1]
        if isinstance(message_id, bytes):
            message_id = message_id.decode("utf-8")
        return str(message_id), fields

    @staticmethod
    def _extract_body(fields: Any) -> Optional[str]:
        if fields is None:
            return None
        if isinstance(fields, dict):
            raw = fields.get(_BODY_FIELD)
            if raw is None:
                raw = fields.get(_BODY_FIELD.encode("utf-8"))
        elif isinstance(fields, (list, tuple)):
            # flat key/value list from some redis clients
            mapping = {}
            for i in range(0, len(fields) - 1, 2):
                mapping[fields[i]] = fields[i + 1]
            raw = mapping.get(_BODY_FIELD)
            if raw is None:
                raw = mapping.get(_BODY_FIELD.encode("utf-8"))
        else:
            return None
        if raw is None:
            return None
        if isinstance(raw, bytes):
            return raw.decode("utf-8")
        return str(raw)


def migrate_redis_list_to_stream(
    redis_client: Any,
    list_key: str,
    stream_key: Optional[str] = None,
) -> int:
    """
    Move messages from a legacy Redis List queue into a Stream.

    Pops from ``list_key`` with ``RPOP`` (same end workers used to consume) and
    ``XADD``s to ``stream_key``.

    **Same-key migration is not supported:** a Redis key cannot be both a list
    and a stream. Pass a distinct ``stream_key``, or drain the list then use a
    new key for Streams workers. If ``stream_key`` is omitted, messages are
    written to ``{list_key}:stream``.

    Returns the number of messages migrated.
    """
    target = stream_key if stream_key is not None else f"{list_key}:stream"
    if target == list_key:
        raise ValueError(
            "stream_key must differ from list_key; a Redis key cannot be both "
            "a list and a stream. Use a new stream key or drain then recreate."
        )
    migrated = 0
    while True:
        raw = redis_client.rpop(list_key)
        if raw is None:
            break
        body = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
        redis_client.xadd(target, {_BODY_FIELD: body})
        migrated += 1
    return migrated


class RedisCommandBusAdapter(RedisQueueAdapter):
    """Deprecated alias for :class:`RedisQueueAdapter`."""

    def __init__(self, redis_client: Any, queue_name: str, **kwargs: Any) -> None:
        warnings.warn(
            "RedisCommandBusAdapter is deprecated; use RedisQueueAdapter instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(redis_client=redis_client, queue_name=queue_name, **kwargs)
