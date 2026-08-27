# Pub/sub events (fan-out)

Commands use **competing consumers** (one message → one worker). Events use **fan-out**: one `publish` → every subscribed worker gets a copy.

## Quick start

```python
from command_bus import EventBus, CommandBusRouter
from command_bus.adapters import InMemoryPubSubAdapter

router = CommandBusRouter()
adapter = InMemoryPubSubAdapter(queue_name="order-events")
bus = EventBus(queue_adapter=adapter, command_router=router)

@router.event()
def on_order_created(order_id: str, amount_cents: int):
    print(f"Order {order_id}: {amount_cents}")

# Producer (no local handler required)
await bus.publish(on_order_created(order_id="ord-1", amount_cents=1999))

# Each worker process with its own adapter instance on the same topic:
await bus.work()
```

With Redis or RabbitMQ, give **each worker its own adapter instance** subscribed to the same topic name. Every worker then receives the published event.

## Command vs event

| | CommandBus | EventBus |
|--|------------|----------|
| Message base | `CommandMessage` | `EventMessage` |
| Send API | `execute(...)` | `publish(...)` |
| Handler required to send? | Yes (local registry) | No |
| Response / wait | Optional (`response_store`) | No |
| Transport | Work queues (one consumer) | Fan-out pub/sub |
| Decorator | `@router.command()` | `@router.event()` |

## Fan-out adapters

### In-memory

**`InMemoryPubSubAdapter(queue_name="events")`** – each instance is one subscriber. `enqueue` copies the body to every subscriber on that topic. Good for tests and single-process multi-worker simulation.

### Redis Pub/Sub

**`RedisPubSubAdapter(redis_client, queue_name)`** – `PUBLISH` / `SUBSCRIBE` on `queue_name` as the channel. Extra: `[redis]`.

```python
import redis
from command_bus import EventBus
from command_bus.adapters import RedisPubSubAdapter

r = redis.Redis(host="localhost", port=6379)
adapter = RedisPubSubAdapter(redis_client=r, queue_name="order-events")
bus = EventBus(queue_adapter=adapter)
```

Call **`adapter.close()`** when shutting down a worker to stop the listener thread.

### RabbitMQ fanout

**`RabbitMqFanoutAdapter(queue_name, connection_url=...)`** – durable fanout exchange named `queue_name`. Each consumer declares an exclusive auto-delete queue bound to the exchange. Extra: `[rabbitmq]`.

```python
from command_bus.adapters import RabbitMqFanoutAdapter

adapter = RabbitMqFanoutAdapter(
    queue_name="order-events",
    connection_url="amqp://guest:guest@localhost/",
)
```

Call **`adapter.close()`** when shutting down workers.

### SNS (with SQS subscriptions)

**`SnsPubSubAdapter(topic_arn, sns_client, sqs_client=None, queue_url=None, message_parser_class=None)`** – publishes to an SNS topic using optional parser hooks (`dumps`, `subject`, `message_attributes`). Each worker polls its own SQS queue when consuming. Omit `sqs_client` and `queue_url` for publish-only. Extra: `[sns]` or `[boto3]`.

```python
import boto3
from command_bus import EventBus, CommandBusRouter
from command_bus.adapters import SnsPubSubAdapter

sns = boto3.client("sns")
sqs = boto3.resource("sqs")

adapter = SnsPubSubAdapter(
    topic_arn="arn:aws:sns:us-east-1:123456789012:order-events",
    sns_client=sns,
    sqs_client=sqs,
    queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/worker-a",
    message_parser_class=MyEnvelopeParser,
)
bus = EventBus(
    queue_adapter=adapter,
    command_router=CommandBusRouter(),
    message_parser_class=MyEnvelopeParser,
)
```

Give **each worker its own SQS queue** subscribed to the same SNS topic (standard AWS fan-out). The adapter unwraps the SNS notification envelope automatically when polling SQS.

## Multi-worker example

```python
# shared.py
from command_bus import EventBus, CommandBusRouter
from command_bus.adapters import RedisPubSubAdapter
import redis

router = CommandBusRouter()

@router.event()
def on_order_created(order_id: str):
    ...

def make_bus():
    r = redis.Redis()
    return EventBus(
        queue_adapter=RedisPubSubAdapter(r, "order-events"),
        command_router=router,
    )

# worker module
from shared import make_bus
bus = make_bus()
# command-bus-worker myapp.worker:bus --workers 4
# all four processes receive each published event
```

You can also put an `EventBus` next to a `CommandBus` in a [`CommandBusGroup`](cli.md).

## Out of scope

Response-store on events is not supported. Use `CommandBus` when you need request/response.
