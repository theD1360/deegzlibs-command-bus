# Execute and wait (unified API)

**`execute()`** is async and is the single entry point for sending commands. Behaviour depends on whether the bus has a **response store** and on the **`wait`** flag.

## Behaviour

| Scenario | What happens |
|----------|----------------|
| **No response store** | `await bus.execute(command)` only enqueues and returns `None`. `wait` is ignored. |
| **Response store, `wait=True` (default when store is set)** | Bus enqueues the command with a `correlation_id`, then polls the response store until the worker stores the handler result (or timeout). Returns that result. |
| **Response store, `wait=False`** | Only enqueues; returns `None`. Fire-and-forget. |

So:

- **With response store:** `result = await bus.execute(command)` waits for the handler result by default; use `await bus.execute(command, wait=False)` to only enqueue.
- **Without response store:** `await bus.execute(command)` just enqueues.

**`execute_and_wait(command, ...)`** is a convenience for **`execute(command, wait=True, ...)`**.

## Getting responses (request/response)

To get a result back from the worker:

1. Install Redis support: **`pip install deegzlibs-command-bus[redis]`** (or use another response store implementation).
2. Create a **response store** and pass it into the bus. Client and worker must use the **same store** (e.g. same Redis instance).
3. **Client:** call **`result = await bus.execute(command)`** or **`result = await bus.execute_and_wait(command, timeout_seconds=30)`**.
4. **Worker:** no change. After each handler runs, if the command has a `correlation_id` and the bus has a `response_store`, the last non-`None` return value is stored under that id.

Handler return values must be JSON-serializable (or Pydantic models; they are stored via `model_dump()`).

### Example: class-based handler

```python
import boto3
import redis
from command_bus import CommandBus, CommandBusRouter
from command_bus.adapters import SqsCommandBusAdapter, RedisResponseStore

router = CommandBusRouter()
router.register(OrderCreated, SendOrderConfirmation)

def create_bus():
    r = redis.Redis(host="localhost", port=6379, decode_responses=False)
    response_store = RedisResponseStore(r, key_prefix="myapp:response:", default_ttl_seconds=60)
    adapter = SqsCommandBusAdapter(queue_name="orders", sqs_client=boto3.resource("sqs"))
    bus = CommandBus(queue_adapter=adapter, command_router=router, response_store=response_store)
    return bus

# Client
async def main():
    bus = create_bus()
    result = await bus.execute_and_wait(OrderCreated(order_id="ord-1", amount_cents=1999), timeout_seconds=10)
    print(result)  # whatever the handler returned
```

### Example: with `@router.command()`

The decorated function's return value is what the client receives. Use the message factory with `execute` or `execute_and_wait`:

```python
@router.command()
def process_order(order_id: str, amount_cents: int) -> dict:
    # do work...
    return {"status": "processed", "order_id": order_id}

# Client
bus = create_bus()
result = await bus.execute(process_order(order_id="ord-1", amount_cents=1999))  # default wait=True
# or: result = await bus.execute_and_wait(process_order(order_id="ord-1", amount_cents=1999), timeout_seconds=10)
```

## Timeout

If the worker never stores a result (handler doesn't return or raises), the client gets **`TimeoutError`** after **`timeout_seconds`** (default 30). You can pass **`timeout_seconds`**, **`poll_interval_seconds`**, and **`response_ttl_seconds`** to **`execute()`** or **`execute_and_wait()`**.

## Response store implementations

- **InMemoryResponseStore** – In-memory (no deps). Useful for tests. From **`command_bus.adapters`**.
- **RedisResponseStore** – Redis-backed. Install with **`pip install deegzlibs-command-bus[redis]`**. From **`command_bus.adapters`**.
