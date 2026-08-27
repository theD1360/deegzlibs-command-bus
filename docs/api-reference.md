# API reference

High-level overview of public types and methods. For details, see the source or docstrings.

## Core

### CommandMessage

Base class for command payloads (Pydantic `BaseModel`). Subclass it to define your command schema.

- **`correlation_id: Optional[str] = None`** – Set by the bus when using `execute_and_wait`. The worker's handler return value is stored under this key in the response store.
- **`str(message)`** – Returns the serialized form used when enqueueing (e.g. repr-style for the default parser).

### EventMessage

Base class for pub/sub event payloads. Fire-and-forget; no response-store semantics. See [Pub/sub events](pubsub-events.md).

### Handler

Abstract handler. Subclass and implement **`process(self, message)`**. Can return anything (sync or async). The return value is used when the bus has a response store and the message has a `correlation_id`.

**Deprecated:** **`CommandHandler`** (alias for **`Handler`**).

### Router

Maps message types to handler classes.

- **`register(message_class, handler_class)`** – Register a handler for a message type.
- **`deregister(message_class, handler_class)`** – Remove a registration.
- **`get_handlers_for_message(message_class_or_instance)`** – Return matching router entries.
- **`command()`** – Decorator: build CommandMessage from a function's signature, register a handler, return a message factory. See [Handler decorator](handler-decorator.md).
- **`event()`** – Same pattern for EventMessage / EventBus.publish. See [Pub/sub events](pubsub-events.md).

**Deprecated:** **`CommandBusRouter`** (alias for **`Router`**), **`CommandBusRouterEntry`** (alias for **`RouterEntry`**).

### BusGroup / WorkerConfig

Declarative layout for the [Worker CLI](cli.md) when you want **several `CommandBus` or `EventBus` instances** in one supervised process tree. Point the CLI at **`module:attribute`** where `attribute` is the `BusGroup` (e.g. `myapp.worker:bus_group`).

- **`BusGroup(*WorkerConfig)`** – At least one config. **`validate(module)`** checks each bus and binding. **`iter_jobs(module, default_workers)`** returns the `(bus_attr, worker_index)` list used to spawn processes.

**Deprecated:** **`CommandBusGroup`** (alias for **`BusGroup`**).

- **`WorkerConfig(bus, workers=None)`** – **`bus`** is a `CommandBus` or `EventBus`. If **`workers`** is `None`, the CLI **`--workers`** value applies to that entry. Each bus must also be stored on a **top-level attribute** of the worker module so the CLI can resolve a name for subprocesses (**`resolve_bus_attr_on_module(module, bus)`**).

### CommandBus

Generic bus: coordinates a queue adapter and router. **`execute()`** is async.

- **`__init__(queue_adapter, command_router=None, message_parser_class=None, response_store=None, response_ttl_seconds=60)`**
- **`await execute(message_instance, delay_seconds=None, wait=None, timeout_seconds=30, poll_interval_seconds=0.5, response_ttl_seconds=None)`** – Enqueue and optionally wait for handler result. See [Execute and wait](execute-and-wait.md).
- **`await execute_and_wait(message_instance, timeout_seconds=30, ...)`** – Convenience for `execute(..., wait=True)`.
- **`await dispatch(raw_message: str)`** – Parse the raw message and run all registered handlers (used internally by `work()`).
- **`await work()`** – Poll the queue and dispatch each message.

For running **`work()`** in multiple OS processes from the shell, see [Worker CLI](cli.md) (`command-bus-worker`).

### EventBus

Pub/sub bus: coordinates a fan-out adapter and router. **`publish()`** is async.

- **`__init__(queue_adapter, command_router=None, message_parser_class=None)`**
- **`await publish(message_instance, delay_seconds=None)`** – Broadcast to all subscribers (no local handler required).
- **`await dispatch(raw_message)`** / **`await work()`** – Same consumer loop as CommandBus; missing handlers are a no-op.

See [Pub/sub events](pubsub-events.md).

### get_qual_name(obj)

Return the qualified name (module + class name) for a class or instance. Used for message matching.

## Parsers

- **MessageParser** / **ReprMessageParser** – Default parser for repr-style strings.
- **JsonMessageParser** – Parser for JSON (type field + kwargs). Optional **MessageCodec** wrapper; **`JsonMessageParser.dumps(...)`** for serialization.
- **Base64MessageParser** – Base64-encoded (optionally gzip) payloads; uses an inner parser.
- **MessageCodec** – Optional encode/decode wrapper (**Base64MessageCodec**, **GzipMessageCodec**, **ChainedMessageCodec**, **configure_json_parser**).
- **MessageParserBase** – Abstract base; **`initialize()`**, **`dumps()`**, optional **`subject()`** / **`message_attributes()`**.

Set the parser when creating the bus: **`message_parser_class=...`**.

## Queue adapters (QueueAdapter)

Implement **`enqueue(message_instance, delay_seconds=0)`**, **`dequeue(message_instance)`**, **`get_messages(...)`**.

- **InMemoryQueueAdapter** – In-memory FIFO.
- **SqsQueueAdapter** – AWS SQS. Extra: `[sqs]` or `[boto3]`.
- **RabbitMqQueueAdapter** – RabbitMQ. Extra: `[rabbitmq]`.
- **RedisQueueAdapter** – Redis Lists. Extra: `[redis]`.
- **InMemoryPubSubAdapter** – In-memory fan-out.
- **RedisPubSubAdapter** – Redis Pub/Sub. Extra: `[redis]`.
- **RabbitMqFanoutAdapter** – RabbitMQ fanout exchange. Extra: `[rabbitmq]`.
- **SnsPubSubAdapter** – AWS SNS fan-out (SQS subscriptions). Extra: `[sns]` or `[boto3]`.

**Deprecated queue adapter names:** `InMemoryCommandBusAdapter`, `SqsCommandBusAdapter`, `RabbitMqCommandBusAdapter`, `RedisCommandBusAdapter`, and **`CommandBusAdapter`** (alias for **`QueueAdapter`**).

## Response store (ResponseStore)

Implement **`set(key, value, ttl_seconds=60)`**, **`get(key)`**, **`delete(key)`**.

- **InMemoryResponseStore** – In-memory.
- **RedisResponseStore** – Redis. Extra: `[redis]`.

## Interfaces

- **QueueAdapter** – Abstract queue contract.
- **CommandBusAdapter** – Deprecated alias for **QueueAdapter**.
- **CommandBusInterface** – Abstract command bus contract.
- **EventBusInterface** – Abstract event bus contract.
- **RouterInterface** – Abstract router contract.
- **CommandBusRouterInterface** – Deprecated alias for **RouterInterface**.
- **ResponseStore** – Abstract response store contract.
