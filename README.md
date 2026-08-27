# DeegzLibs CommandBus (Python)

A small command and event bus with pluggable queue adapters. Define messages as Pydantic models, register handlers, and run commands (one worker) or publish events (fan-out) in-process or via a queue (e.g. AWS SQS, SNS, RabbitMQ, Redis).

## Installation

```bash
pip install deegzlibs-command-bus
```

Optional extras: **`[sqs]`**, **`[sns]`**, **`[boto3]`**, **`[redis]`**, **`[rabbitmq]`**. See [Installation](docs/installation.md).

## Quick start

### Commands

One message is handled by **one worker** (competing consumers):

```python
from command_bus import CommandBus, Router, CommandMessage, Handler
from command_bus.adapters import InMemoryQueueAdapter

router = Router()
adapter = InMemoryQueueAdapter(queue_name="commands")
bus = CommandBus(queue_adapter=adapter, command_router=router)

@router.command()
def on_order_created(order_id: str, amount_cents: int):
    print(f"Order {order_id}: {amount_cents} cents")

# Fire-and-forget
await bus.execute(on_order_created(order_id="ord-1", amount_cents=1999), wait=False)

# Worker: poll and dispatch
await bus.work()
```

### Events

One publish reaches **every subscriber** (fan-out):

```python
from command_bus import EventBus, Router
from command_bus.adapters import InMemoryPubSubAdapter

router = Router()
adapter = InMemoryPubSubAdapter(queue_name="order-events")
bus = EventBus(queue_adapter=adapter, command_router=router)

@router.event()
def on_order_created(order_id: str, amount_cents: int):
    print(f"Order {order_id}: {amount_cents} cents")

# Producer (no local handler required)
await bus.publish(on_order_created(order_id="ord-1", amount_cents=1999))

# Each worker with its own adapter on the same topic receives the event
await bus.work()
```

To run workers as **separate OS processes** (useful when handlers do a lot of CPU work), use the built-in CLI, e.g. **`command-bus-worker myapp.worker:bus --workers 4`** (omit **`:bus`** if your bus lives on attribute **`bus`**). For several queues in one supervised tree, point at a **`BusGroup`**, e.g. **`myapp.worker:bus_group`** (see [Worker CLI](docs/cli.md)).

For full examples (messages, handlers, SQS/Redis/SNS, execute-and-wait), see the [documentation](docs/index.md).

## Documentation

| Topic | Description |
|-------|-------------|
| [Installation](docs/installation.md) | Package and extras. |
| [Quick start](docs/quickstart.md) | Messages, handlers, register, execute, publish. |
| [Handler decorator](docs/handler-decorator.md) | `@router.command()` and message factory. |
| [Message formats and parsers](docs/message-formats-and-parsers.md) | Repr, JSON, Base64, custom parser. |
| [Client and worker](docs/client-and-worker.md) | Shared module, producer, consumer. |
| [Worker CLI](docs/cli.md) | `command-bus-worker module[:attr]` — `CommandBus`, `EventBus`, or `BusGroup`. |
| [Queue adapters](docs/queue-adapters.md) | In-memory, SQS, RabbitMQ, Redis. |
| [Pub/sub events](docs/pubsub-events.md) | EventBus, fan-out adapters, `@router.event()`. |
| [Execute and wait](docs/execute-and-wait.md) | Response store, request/response. |
| [API reference](docs/api-reference.md) | Types and methods overview. |

## License

MIT
