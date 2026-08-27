# DeegzLibs CommandBus (Python)

A small command bus with pluggable queue adapters. Define command messages as Pydantic models, register handlers, and execute commands in-process or via a queue (e.g. AWS SQS, RabbitMQ, Redis).

## Installation

```bash
pip install deegzlibs-command-bus
```

Optional extras: **`[sqs]`**, **`[sns]`**, **`[boto3]`**, **`[redis]`**, **`[rabbitmq]`**. See [Installation](docs/installation.md).

## Quick start

```python
from command_bus import CommandBus, CommandBusRouter, CommandMessage, CommandHandler
from command_bus.adapters import InMemoryCommandBusAdapter

router = CommandBusRouter()
adapter = InMemoryCommandBusAdapter(queue_name="commands")
bus = CommandBus(queue_adapter=adapter, command_router=router)

@router.command()
def on_order_created(order_id: str, amount_cents: int):
    print(f"Order {order_id}: {amount_cents} cents")

# Fire-and-forget
await bus.execute(on_order_created(order_id="ord-1", amount_cents=1999), wait=False)

# Worker: poll and dispatch
await bus.work()
```

To run workers as **separate OS processes** (useful when handlers do a lot of CPU work), use the built-in CLI, e.g. **`command-bus-worker myapp.worker:bus --workers 4`** (omit **`:bus`** if your bus lives on attribute **`bus`**). For several queues in one supervised tree, point at a **`CommandBusGroup`**, e.g. **`myapp.worker:command_bus_group`** (see [Worker CLI](docs/cli.md)).

For full examples (messages, handlers, SQS/Redis, execute-and-wait), see the [documentation](docs/index.md).

## Documentation

| Topic | Description |
|-------|-------------|
| [Installation](docs/installation.md) | Package and extras. |
| [Quick start](docs/quickstart.md) | Messages, handlers, register, execute. |
| [Handler decorator](docs/handler-decorator.md) | `@router.command()` and message factory. |
| [Message formats and parsers](docs/message-formats-and-parsers.md) | Repr, JSON, Base64, custom parser. |
| [Client and worker](docs/client-and-worker.md) | Shared module, producer, consumer. |
| [Worker CLI](docs/cli.md) | `command-bus-worker module[:attr]` — `CommandBus` or `CommandBusGroup`, fork/spawn. |
| [Queue adapters](docs/queue-adapters.md) | In-memory, SQS, RabbitMQ, Redis. |
| [Pub/sub events](docs/pubsub-events.md) | EventBus, fan-out adapters, `@router.event()`. |
| [Execute and wait](docs/execute-and-wait.md) | Response store, request/response. |
| [API reference](docs/api-reference.md) | Types and methods overview. |

## License

MIT
