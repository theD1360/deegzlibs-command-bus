# Quick start

## 1. Define command messages

Subclass `CommandMessage` (a Pydantic model). Use it for the payload of your commands.

```python
from command_bus import CommandMessage

class OrderCreated(CommandMessage):
    order_id: str
    amount_cents: int
```

## 2. Define handlers

Implement `CommandHandler`: define a class with a `process(self, message)` method. The method can be sync or async.

```python
from command_bus import CommandMessage, CommandHandler

class SendOrderConfirmation(CommandHandler):
    def process(self, message: CommandMessage):
        print(f"Order {message.order_id} confirmed")
```

## 3. Register and execute

Create a router, register the message type with the handler, then use a bus (with a queue adapter) to execute commands. The bus enqueues the message; a worker later runs `await bus.work()` to dispatch to handlers.

```python
from command_bus import CommandBus, CommandBusRouter
from command_bus.adapters import InMemoryCommandBusAdapter

router = CommandBusRouter()
router.register(OrderCreated, SendOrderConfirmation)

adapter = InMemoryCommandBusAdapter(queue_name="commands")
bus = CommandBus(queue_adapter=adapter, command_router=router)

# Enqueue a command (fire-and-forget)
await bus.execute(OrderCreated(order_id="ord-1", amount_cents=1999), wait=False)

# Worker: poll queue and run handlers
await bus.work()
```

## Dispatching without a queue

If you don't use a queue adapter, you can parse a message string and dispatch in-process:

```python
from command_bus import MessageParser

msg_str = "your.module.OrderCreated(order_id='abc', amount_cents=1999)"
parser = MessageParser(msg_str)
command = parser.initialize()
for entry in router.get_handlers_for_message(command):
    handler = entry.handler_instance()
    await handler(command)
```

## Next steps

- Use the **[handler decorator](handler-decorator.md)** to avoid defining a message class and get a message factory: `bus.execute(on_order_created(order_id=1, amount_cents=10), wait=False)`.
- Configure a **[queue adapter](queue-adapters.md)** (SQS, Redis, RabbitMQ) and a **[client/worker](client-and-worker.md)** setup.
- Use **[execute and wait](execute-and-wait.md)** with a response store to get the handler result back.
