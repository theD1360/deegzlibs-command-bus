# Client and worker

The **client** (producer) sends commands with **`await bus.execute(...)`**. A **worker** (consumer), often in another process or container, polls the queue and runs handlers with **`await bus.work()`**. Both should use the same configuration: same queue name, adapter type, and handler registrations.

## Shared module

Define commands, handlers, and a **single function that builds the bus**. Client and worker import that function so they share configuration.

```python
# commands.py
import boto3
from command_bus import CommandBus, CommandBusRouter, CommandMessage, CommandHandler
from command_bus.adapters import SqsCommandBusAdapter

router = CommandBusRouter()

class OrderCreated(CommandMessage):
    order_id: str
    amount_cents: int

class SendOrderConfirmation(CommandHandler):
    def process(self, message: CommandMessage):
        print(f"Sent confirmation for order {message.order_id}")

router.register(OrderCreated, SendOrderConfirmation)

@router.command()
def on_payment_received(order_id: str, amount_cents: int):
    print(f"Payment received for order {order_id}: {amount_cents} cents")

def create_bus():
    """Shared bus configuration for both client and worker."""
    sqs = boto3.resource("sqs")
    adapter = SqsCommandBusAdapter(queue_name="orders", sqs_client=sqs)
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

## Worker (consumer)

Use the same factory, then poll and dispatch in a loop:

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

## Shutdown

For adapters that hold a connection (e.g. RabbitMQ), you can close it when shutting down the worker:

```python
bus.queue_adapter.close()
```
