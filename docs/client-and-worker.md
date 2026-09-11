# Client and worker

The **standard worker path** is **[`WorkerApp`](worker-app.md)** plus the **`command-bus-worker`** / **`command-bus worker`** CLI. Use that for production processes (lifecycle hooks, concurrency, multi-queue register/mount).

The **client** (producer) still sends with **`await bus.execute(...)`** or **`await app.execute(...)`**. Producers and workers must share the same queue backend and queue name.

## Recommended: WorkerApp

```python
# worker_app.py
from command_bus import WorkerApp, CommandMessage
from command_bus.adapters import RedisQueueAdapter  # or SqsQueueAdapter, etc.
import redis

r = redis.Redis(host="localhost", port=6379)
app = WorkerApp(queue_adapter=RedisQueueAdapter(r, queue_name="orders"))

@app.command()
def send_confirmation(order_id: str, amount_cents: int):
    print(f"Sent confirmation for order {order_id}")

@app.on_startup
def connect_pools():
    ...  # DB / Redis pools, etc.
```

```bash
command-bus-worker myapp.worker_app:app --workers 4
```

See [WorkerApp](worker-app.md) and [CLI](cli.md).

## Shared module (raw CommandBus)

If you need a raw bus factory (tests, thin clients), define commands, handlers, and a **single function that builds the bus**. Client and worker import that function so they share configuration.

```python
# commands.py
import boto3
from command_bus import CommandBus, Router, CommandMessage, Handler
from command_bus.adapters import SqsQueueAdapter

router = Router()

class OrderCreated(CommandMessage):
    order_id: str
    amount_cents: int

class SendOrderConfirmation(Handler):
    def process(self, message: CommandMessage):
        print(f"Sent confirmation for order {message.order_id}")

router.register(OrderCreated, SendOrderConfirmation)

@router.command()
def on_payment_received(order_id: str, amount_cents: int):
    print(f"Payment received for order {order_id}: {amount_cents} cents")

def create_bus():
    """Shared bus configuration for both client and worker."""
    sqs = boto3.resource("sqs")
    adapter = SqsQueueAdapter(queue_name="orders", sqs_client=sqs)
    bus = CommandBus(queue_adapter=adapter, command_router=router)
    return bus
```

## Client (producer)

Get the bus from the shared factory and enqueue commands:

```python
# client.py
from commands import OrderCreated, create_bus

async def main():
    bus = create_bus()
    await bus.execute(OrderCreated(order_id="ord-1", amount_cents=2999), wait=False)
    await bus.execute(OrderCreated(order_id="ord-2", amount_cents=1500), delay_seconds=10, wait=False)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

With the handler decorator you can use the message factory:

```python
from commands import create_bus, on_payment_received

async def main():
    bus = create_bus()
    await bus.execute(on_payment_received(order_id="ord-1", amount_cents=100), wait=False)
```

## Worker loop (raw CommandBus — secondary)

Prefer **WorkerApp + CLI** above. A hand-written loop still works for demos:

```python
# worker.py
import asyncio
from commands import create_bus

async def run_worker():
    bus = create_bus()
    while True:
        await bus.work()  # polls queue, dispatches to handlers, then returns
        await asyncio.sleep(1)  # optional: avoid tight loop when queue is empty

if __name__ == "__main__":
    asyncio.run(run_worker())
```

## Built-in worker CLI

For production-style deployments use the **`command-bus-worker`** entry point. Pass a **target** `module:attribute` (like uvicorn): prefer a **`WorkerApp`**; **`CommandBus`**, **`EventBus`**, and **`BusGroup`** still work. Omit **`:attribute`** to use **`bus`**. The CLI spawns **`--workers`** processes per bus (or uses the group’s `WorkerConfig`); each child imports the module and runs `work()` in its own interpreter so CPU-bound handlers are not limited by a single GIL.

```bash
command-bus-worker myapp.worker:app --workers 4 -v
```

For **several buses in one process tree**, expose a **`WorkerApp`** with `register(...)` or a **`BusGroup`**. See [Worker CLI](cli.md).

## Shutdown

For adapters that hold a connection (e.g. RabbitMQ), close it on worker shutdown. With WorkerApp, prefer **`@app.on_shutdown`**.

```python
bus.queue_adapter.close()
```
