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

**RedisQueueAdapter** – Redis Lists (LPUSH/BRPOP). Install with `pip install deegzlibs-command-bus[redis]`. You can use the same Redis instance for the queue and for the [response store](execute-and-wait.md) (e.g. `execute_and_wait`).

```python
import redis
from command_bus import CommandBus
from command_bus.adapters import RedisQueueAdapter

r = redis.Redis(host="localhost", port=6379)
adapter = RedisQueueAdapter(redis_client=r, queue_name="commands")
bus = CommandBus(queue_adapter=adapter)
```

Constructor: **`RedisQueueAdapter(redis_client, queue_name: str)`**.

- **`delay_seconds`** is not supported (Redis List has no native delay).
- Messages are removed when popped; failed handlers do not automatically requeue.

---

## Fan-out (pub/sub)

For **broadcast** (every worker gets a copy), use the event bus and fan-out adapters instead of the work-queue adapters above. See [Pub/sub events](pubsub-events.md).

- **`InMemoryPubSubAdapter`** – in-process fan-out.
- **`RedisPubSubAdapter`** – Redis PUBLISH/SUBSCRIBE (`[redis]`).
- **`RabbitMqFanoutAdapter`** – RabbitMQ fanout exchange (`[rabbitmq]`).
- **`SnsPubSubAdapter`** – AWS SNS publish with per-worker SQS subscriptions (`[sns]` or `[boto3]`).
