"""Tests for Redis Streams queue adapter (mocked)."""

from unittest.mock import MagicMock, call

import pytest
from command_bus import CommandBus, CommandHandler, CommandMessage, ReleaseMessage, Router
from command_bus.adapters.queue.redis import (
    RedisCommandBusAdapter,
    RedisQueueAdapter,
    _RedisMessage,
    migrate_redis_list_to_stream,
)


class DummyMessage(CommandMessage):
    id: str


def test_redis_message_wrapper_delete_acks():
    adapter = MagicMock(spec=RedisQueueAdapter)
    m = _RedisMessage(body="hello", message_id="1-0", adapter=adapter)
    assert m.body == "hello"
    assert m.message_id == "1-0"
    m.delete()
    adapter._ack.assert_called_once_with("1-0")


def test_redis_adapter_enqueue():
    redis_mock = MagicMock()
    adapter = RedisQueueAdapter(redis_client=redis_mock, queue_name="myqueue")
    msg = DummyMessage(id="x")
    adapter.enqueue(msg, delay_seconds=0)
    redis_mock.xadd.assert_called_once_with("myqueue", {"body": str(msg)})


def test_redis_adapter_ensure_group_on_get_messages():
    redis_mock = MagicMock()
    redis_mock.xautoclaim.return_value = ("0-0", [])
    redis_mock.xreadgroup.return_value = []
    adapter = RedisQueueAdapter(
        redis_client=redis_mock,
        queue_name="q",
        consumer_group="command-bus",
        consumer_name="worker-1",
    )
    assert adapter.get_messages(max_messages=1) == []
    redis_mock.xgroup_create.assert_called_once_with(
        "q", "command-bus", id="0", mkstream=True
    )
    # second call should not recreate
    adapter.get_messages(max_messages=1)
    assert redis_mock.xgroup_create.call_count == 1


def test_redis_adapter_busygroup_is_ok():
    redis_mock = MagicMock()
    redis_mock.xgroup_create.side_effect = Exception("BUSYGROUP Consumer Group name already exists")
    redis_mock.xautoclaim.return_value = ("0-0", [])
    redis_mock.xreadgroup.return_value = []
    adapter = RedisQueueAdapter(redis_client=redis_mock, queue_name="q", consumer_name="c1")
    assert adapter.get_messages() == []


def test_redis_adapter_get_messages_xreadgroup():
    redis_mock = MagicMock()
    redis_mock.xautoclaim.return_value = ("0-0", [])
    redis_mock.xreadgroup.return_value = [
        ("q", [("1-0", {"body": "payload"})])
    ]
    adapter = RedisQueueAdapter(
        redis_client=redis_mock,
        queue_name="q",
        consumer_name="c1",
        default_visibility_timeout=30,
    )
    messages = adapter.get_messages(max_messages=1, wait_seconds=0)
    assert len(messages) == 1
    assert messages[0].body == "payload"
    assert messages[0].message_id == "1-0"
    redis_mock.xreadgroup.assert_called_once()
    kwargs = redis_mock.xreadgroup.call_args.kwargs
    assert kwargs["streams"] == {"q": ">"}
    assert kwargs["count"] == 1
    assert kwargs["block"] is None


def test_redis_adapter_get_messages_blocking():
    redis_mock = MagicMock()
    redis_mock.xautoclaim.return_value = ("0-0", [])
    redis_mock.xreadgroup.return_value = [
        ("q", [("2-0", {"body": b"bytes-payload"})])
    ]
    adapter = RedisQueueAdapter(redis_client=redis_mock, queue_name="q", consumer_name="c1")
    messages = adapter.get_messages(max_messages=1, wait_seconds=5)
    assert messages[0].body == "bytes-payload"
    assert redis_mock.xreadgroup.call_args.kwargs["block"] == 5000


def test_redis_adapter_autoclaim_before_read():
    redis_mock = MagicMock()
    redis_mock.xautoclaim.return_value = (
        "0-0",
        [("1-0", {"body": "reclaimed"})],
    )
    redis_mock.xreadgroup.return_value = []
    adapter = RedisQueueAdapter(
        redis_client=redis_mock,
        queue_name="q",
        consumer_name="c1",
        default_visibility_timeout=10,
    )
    messages = adapter.get_messages(max_messages=2, visibility_timeout=10)
    assert len(messages) == 1
    assert messages[0].body == "reclaimed"
    redis_mock.xautoclaim.assert_called_once()
    ac_kwargs = redis_mock.xautoclaim.call_args.kwargs
    assert ac_kwargs["min_idle_time"] == 10000
    assert ac_kwargs["count"] == 2
    # claimed filled remaining? only 1 claimed, so still reads for 1 more
    redis_mock.xreadgroup.assert_called_once()
    assert redis_mock.xreadgroup.call_args.kwargs["count"] == 1


def test_redis_adapter_dequeue_xack_xdel():
    redis_mock = MagicMock()
    redis_mock.xautoclaim.return_value = ("0-0", [])
    redis_mock.xreadgroup.return_value = [
        ("q", [("1-0", {"body": "msg"})])
    ]
    adapter = RedisQueueAdapter(
        redis_client=redis_mock,
        queue_name="q",
        consumer_group="command-bus",
        consumer_name="c1",
    )
    messages = adapter.get_messages(max_messages=1)
    adapter.dequeue(messages[0])
    redis_mock.xack.assert_called_once_with("q", "command-bus", "1-0")
    redis_mock.xdel.assert_called_once_with("q", "1-0")


def test_redis_adapter_pending_message_count_and_purge():
    redis_mock = MagicMock()
    redis_mock.xlen.return_value = 3
    redis_mock.exists.return_value = 1
    adapter = RedisQueueAdapter(redis_client=redis_mock, queue_name="q", consumer_name="c1")
    assert adapter.pending_message_count() == 3
    assert adapter.purge_messages() == 3
    redis_mock.delete.assert_called_once_with("q")
    assert adapter._group_ensured is False


def test_migrate_redis_list_to_stream():
    redis_mock = MagicMock()
    redis_mock.rpop.side_effect = [b"a", b"b", None]
    n = migrate_redis_list_to_stream(redis_mock, "old-list", "new-stream")
    assert n == 2
    assert redis_mock.xadd.call_args_list == [
        call("new-stream", {"body": "a"}),
        call("new-stream", {"body": "b"}),
    ]


def test_migrate_redis_list_to_stream_default_key():
    redis_mock = MagicMock()
    redis_mock.rpop.side_effect = ["one", None]
    n = migrate_redis_list_to_stream(redis_mock, "commands")
    assert n == 1
    redis_mock.xadd.assert_called_once_with("commands:stream", {"body": "one"})


def test_migrate_same_key_raises():
    with pytest.raises(ValueError, match="must differ"):
        migrate_redis_list_to_stream(MagicMock(), "same", "same")


def test_deprecated_alias():
    with pytest.warns(DeprecationWarning):
        RedisCommandBusAdapter(redis_client=MagicMock(), queue_name="q")


@pytest.mark.asyncio
async def test_redis_command_bus_execute_and_work():
    redis_mock = MagicMock()
    redis_mock.xautoclaim.return_value = ("0-0", [])
    redis_mock.xreadgroup.return_value = None
    adapter = RedisQueueAdapter(redis_client=redis_mock, queue_name="events", consumer_name="c1")
    registry = Router()

    class Handler(CommandHandler):
        def process(self, message):
            pass

    registry.register(DummyMessage, Handler)
    bus = CommandBus(queue_adapter=adapter, command_router=registry)
    await bus.execute(DummyMessage(id="a"), wait=False)
    redis_mock.xadd.assert_called_once()
    assert "a" in redis_mock.xadd.call_args[0][1]["body"]
    assert await bus.work() == 0


@pytest.mark.asyncio
async def test_redis_work_acks_on_success():
    redis_mock = MagicMock()
    payload = str(DummyMessage(id="a"))
    redis_mock.xautoclaim.return_value = ("0-0", [])
    redis_mock.xreadgroup.return_value = [("q", [("1-0", {"body": payload})])]
    adapter = RedisQueueAdapter(
        redis_client=redis_mock,
        queue_name="q",
        consumer_group="command-bus",
        consumer_name="c1",
    )
    registry = Router()

    class Handler(CommandHandler):
        def process(self, message):
            return "ok"

    registry.register(DummyMessage, Handler)
    bus = CommandBus(queue_adapter=adapter, command_router=registry)
    assert await bus.work() == 1
    redis_mock.xack.assert_called_once_with("q", "command-bus", "1-0")
    redis_mock.xdel.assert_called_once_with("q", "1-0")


@pytest.mark.asyncio
async def test_redis_work_release_message_skips_ack():
    redis_mock = MagicMock()
    payload = str(DummyMessage(id="a"))
    redis_mock.xautoclaim.return_value = ("0-0", [])
    redis_mock.xreadgroup.return_value = [("q", [("1-0", {"body": payload})])]
    adapter = RedisQueueAdapter(
        redis_client=redis_mock,
        queue_name="q",
        consumer_group="command-bus",
        consumer_name="c1",
    )
    registry = Router()

    class Handler(CommandHandler):
        def process(self, message):
            raise ReleaseMessage()

    registry.register(DummyMessage, Handler)
    bus = CommandBus(queue_adapter=adapter, command_router=registry)
    assert await bus.work() == 1
    redis_mock.xack.assert_not_called()
    redis_mock.xdel.assert_not_called()


@pytest.mark.asyncio
async def test_redis_reclaim_after_unacked():
    """Simulate crash (no ack): next poll autoclaims the idle pending message."""
    redis_mock = MagicMock()
    payload = str(DummyMessage(id="a"))
    redis_mock.xautoclaim.side_effect = [
        ("0-0", []),  # first poll: nothing idle
        ("0-0", [("1-0", {"body": payload})]),  # second poll: reclaim
    ]
    redis_mock.xreadgroup.side_effect = [
        [("q", [("1-0", {"body": payload})])],
        [],
    ]
    adapter = RedisQueueAdapter(
        redis_client=redis_mock,
        queue_name="q",
        consumer_name="c1",
        default_visibility_timeout=1,
    )
    registry = Router()
    calls = {"n": 0}

    class Handler(CommandHandler):
        def process(self, message):
            calls["n"] += 1
            if calls["n"] == 1:
                raise ReleaseMessage()
            return "ok"

    registry.register(DummyMessage, Handler)
    bus = CommandBus(queue_adapter=adapter, command_router=registry)

    assert await bus.work() == 1
    redis_mock.xack.assert_not_called()

    assert await bus.work() == 1
    assert calls["n"] == 2
    redis_mock.xack.assert_called_once()
