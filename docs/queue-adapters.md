# Queue adapters

The bus uses a **QueueAdapter** to enqueue and dequeue messages. Adapters are responsible for transport only; the bus handles parsing and handler dispatch.

> **Note:** Older names (`CommandBusAdapter`, `InMemoryCommandBusAdapter`, `SqsCommandBusAdapter`, etc.) still work but are deprecated. See [API reference](api-reference.md).

## In-memory

**InMemoryQueueAdapter** – FIFO queue in process. No extra dependencies. Useful for tests or single-process use. `delay_seconds` is ignored.

```python
from command_bus import CommandBus
from command_bus.adapters import InMemoryQueueAdapter

adapter = InMemoryQueueAdapter(queue_name="commands")
bus = CommandBus(queue_adapter=adapter)
```

Constructor: **`InMemoryQueueAdapter(queue_name: str = "default")`**

---

## SQS

**SqsQueueAdapter** – AWS SQS. Install with `pip install deegzlibs-command-bus[sqs]`.

```python
import boto3
from command_bus import CommandBus, Router
from command_bus.adapters import SqsQueueAdapter

sqs = boto3.resource("sqs")
adapter = SqsQueueAdapter(queue_name="my-commands", sqs_client=sqs)
router = Router()
bus = CommandBus(queue_adapter=adapter, command_router=router)
```

Constructor: **`SqsQueueAdapter(queue_name: str, sqs_client)`** – `sqs_client` is a boto3 SQS resource.

---

## RabbitMQ

**RabbitMqQueueAdapter** – RabbitMQ via pika. Install with `pip install deegzlibs-command-bus[rabbitmq]`.

```python
from command_bus import CommandBus
from command_bus.adapters import RabbitMqQueueAdapter

adapter = RabbitMqQueueAdapter(
    queue_name="my-commands",
    connection_url="amqp://guest:guest@localhost/",
)
# Or: connection_params=pika.ConnectionParameters(host='localhost', port=5672)
bus = CommandBus(queue_adapter=adapter)
```

Constructor: **`RabbitMqQueueAdapter(queue_name, connection_url=None, connection_params=None)`** – provide either `connection_url` or `connection_params`.

- **`delay_seconds`** is not supported by plain RabbitMQ (use a delayed-message plugin if needed).
- The adapter keeps a single connection for consuming. Call **`adapter.close()`** when shutting down workers to release it.

---

## Redis

**RedisQueueAdapter** – Redis Streams with a consumer group (at-least-once). Requires **Redis ≥ 6.2** (`XAUTOCLAIM`). Install with `pip install deegzlibs-command-bus[redis]`. You can use the same Redis instance for the queue and for the [response store](execute-and-wait.md) (e.g. `execute_and_wait`).

```python
import redis
from command_bus import CommandBus
from command_bus.adapters import RedisQueueAdapter

r = redis.Redis(host="localhost", port=6379)
adapter = RedisQueueAdapter(redis_client=r, queue_name="commands")
bus = CommandBus(queue_adapter=adapter)
```

Constructor: **`RedisQueueAdapter(redis_client, queue_name, *, consumer_group="command-bus", consumer_name=None, default_visibility_timeout=60)`**.

| Method | Redis command |
|--------|----------------|
| `enqueue` | `XADD` (field `body`) |
| `get_messages(..., visibility_timeout=…)` | `XAUTOCLAIM` (idle ≥ VT) then `XREADGROUP` |
| `dequeue` / `message.delete()` | `XACK` + `XDEL` |
| `pending_message_count` | `XLEN` |
| `purge_messages` | `DELETE` key |

- **Visibility timeout** is real: crash before ack leaves the message in the pending entries list; after `visibility_timeout` seconds another poll can reclaim it via `XAUTOCLAIM`.
- Delivery is **at-least-once**. Handlers must be **idempotent** (ack can fail after a successful handler).
- **`delay_seconds`** is not supported.
- Use a **single consumer group** per logical worker fleet (default `command-bus`). A second group on the same stream would duplicate processing.
- Failed handlers still ack by default (see [WorkerApp ack policy](worker-app.md)). Raise **`ReleaseMessage`** to skip ack and retry after VT.

### Migrating from Redis Lists (pre-3.0)

v3.0 replaced Lists (`LPUSH`/`BRPOP`) with Streams. A Redis key cannot be both a list and a stream (`WRONGTYPE`).

1. Drain old list workers, **or** migrate with:

```python
from command_bus.adapters import migrate_redis_list_to_stream

# Target must differ from the list key (a key cannot be both list and stream)
n = migrate_redis_list_to_stream(r, "commands", "commands:v3")
# or default target "{list_key}:stream"
n = migrate_redis_list_to_stream(r, "commands")
```

2. Point producers and workers at the stream key (and Redis ≥ 6.2).
3. Delete the old list key after cutover.

### Downstream adoption checklist

After upgrading to `deegzlibs-command-bus>=3.0.0`:

1. Bump the dependency; ensure Redis ≥ 6.2.
2. Migrate or drain any list keys.
3. Run workers via **`WorkerApp`** + `command-bus-worker` (not a custom BRPOP loop).
4. Remove app-level reclaim that only compensated for destructive list pops.
5. Prefer **no per-tenant queue locks**; if serialization is ever needed, optional middleware can raise `ReleaseMessage` when busy.
6. Smoke: enqueue → crash mid-handler → message reappears after VT → completes; `command-bus count|drain|purge` against the WorkerApp target.

---

## Fan-out (pub/sub)

For **broadcast** (every worker gets a copy), use the event bus and fan-out adapters instead of the work-queue adapters above. See [Pub/sub events](pubsub-events.md).

- **`InMemoryPubSubAdapter`** – in-process fan-out.
- **`RedisPubSubAdapter`** – Redis PUBLISH/SUBSCRIBE (`[redis]`).
- **`RabbitMqFanoutAdapter`** – RabbitMQ fanout exchange (`[rabbitmq]`).
- **`SnsPubSubAdapter`** – AWS SNS publish with per-worker SQS subscriptions (`[sns]` or `[boto3]`).
