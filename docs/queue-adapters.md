# Queue adapters

The bus uses a **CommandBusAdapter** to enqueue and dequeue messages. Adapters are responsible for transport only; the bus handles parsing and handler dispatch.

## In-memory

**InMemoryCommandBusAdapter** – FIFO queue in process. No extra dependencies. Useful for tests or single-process use. `delay_seconds` is ignored.

```python
from command_bus import CommandBus, CommandBusRouter
from command_bus.adapters import InMemoryCommandBusAdapter

adapter = InMemoryCommandBusAdapter(queue_name="commands")
bus = CommandBus(queue_adapter=adapter)
```

Constructor: **`InMemoryCommandBusAdapter(queue_name: str = "default")`**

---

## SQS

**SqsCommandBusAdapter** – AWS SQS. Install with `pip install deegzlibs-command-bus[sqs]`.

```python
import boto3
from command_bus import CommandBus, CommandBusRouter
from command_bus.adapters import SqsCommandBusAdapter

sqs = boto3.resource("sqs")
adapter = SqsCommandBusAdapter(queue_name="my-commands", sqs_client=sqs)
router = CommandBusRouter()
bus = CommandBus(queue_adapter=adapter, command_router=router)
```

Constructor: **`SqsCommandBusAdapter(queue_name: str, sqs_client)`** – `sqs_client` is a boto3 SQS resource.

---

## RabbitMQ

**RabbitMqCommandBusAdapter** – RabbitMQ via pika. Install with `pip install deegzlibs-command-bus[rabbitmq]`.

```python
from command_bus import CommandBus, CommandBusRouter
from command_bus.adapters import RabbitMqCommandBusAdapter

adapter = RabbitMqCommandBusAdapter(
    queue_name="my-commands",
    connection_url="amqp://guest:guest@localhost/",
)
# Or: connection_params=pika.ConnectionParameters(host='localhost', port=5672)
bus = CommandBus(queue_adapter=adapter)
```

Constructor: **`RabbitMqCommandBusAdapter(queue_name, connection_url=None, connection_params=None)`** – provide either `connection_url` or `connection_params`.

- **`delay_seconds`** is not supported by plain RabbitMQ (use a delayed-message plugin if needed).
- The adapter keeps a single connection for consuming. Call **`adapter.close()`** when shutting down workers to release it.

---

## Redis

**RedisCommandBusAdapter** – Redis Lists (LPUSH/BRPOP). Install with `pip install deegzlibs-command-bus[redis]`. You can use the same Redis instance for the queue and for the [response store](execute-and-wait.md) (e.g. `execute_and_wait`).

```python
import redis
from command_bus import CommandBus
from command_bus.adapters import RedisCommandBusAdapter

r = redis.Redis(host="localhost", port=6379)
adapter = RedisCommandBusAdapter(redis_client=r, queue_name="commands")
bus = CommandBus(queue_adapter=adapter)
```

Constructor: **`RedisCommandBusAdapter(redis_client, queue_name: str)`**.

- **`delay_seconds`** is not supported (Redis List has no native delay).
- Messages are removed when popped; failed handlers do not automatically requeue.
