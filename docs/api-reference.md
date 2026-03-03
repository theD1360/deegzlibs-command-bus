# API reference

High-level overview of public types and methods. For details, see the source or docstrings.

## Core

### CommandMessage

Base class for command payloads (Pydantic `BaseModel`). Subclass it to define your command schema.

- **`correlation_id: Optional[str] = None`** – Set by the bus when using `execute_and_wait`. The worker's handler return value is stored under this key in the response store.
- **`str(message)`** – Returns the serialized form used when enqueueing (e.g. repr-style for the default parser).

### CommandHandler

Abstract handler. Subclass and implement **`process(self, message: CommandMessage)`**. Can return anything (sync or async). The return value is used when the bus has a response store and the message has a `correlation_id`.

### CommandBusRouter

Maps message types to handler classes.

- **`register(message_class, handler_class)`** – Register a handler for a message type.
- **`deregister(message_class, handler_class)`** – Remove a registration.
- **`get_handlers_for_message(message_class_or_instance)`** – Return matching router entries.
- **`command()`** – Decorator: build CommandMessage from a function's signature, register a handler, return a message factory. See [Handler decorator](handler-decorator.md).

### CommandBus

Generic bus: coordinates a queue adapter and router. **`execute()`** is async.

- **`__init__(queue_adapter, command_router=None, message_parser_class=None, response_store=None, response_ttl_seconds=60)`**
- **`await execute(message_instance, delay_seconds=None, wait=None, timeout_seconds=30, poll_interval_seconds=0.5, response_ttl_seconds=None)`** – Enqueue and optionally wait for handler result. See [Execute and wait](execute-and-wait.md).
- **`await execute_and_wait(message_instance, timeout_seconds=30, ...)`** – Convenience for `execute(..., wait=True)`.
- **`await dispatch(raw_message: str)`** – Parse the raw message and run all registered handlers (used internally by `work()`).
- **`await work()`** – Poll the queue and dispatch each message.

### get_qual_name(obj)

Return the qualified name (module + class name) for a class or instance. Used for message matching.

## Parsers

- **MessageParser** / **ReprMessageParser** – Default parser for repr-style strings.
- **JsonMessageParser** – Parser for JSON (type field + kwargs).
- **Base64MessageParser** – Base64-encoded (optionally gzip) payloads; uses an inner parser.
- **MessageParserBase** – Abstract base; implement **`initialize() -> CommandMessage`** for custom formats.

Set the parser when creating the bus: **`message_parser_class=...`**.

## Queue adapters (CommandBusAdapter)

Implement **`enqueue(message_instance, delay_seconds=0)`**, **`dequeue(message_instance)`**, **`get_messages(...)`**.

- **InMemoryCommandBusAdapter** – In-memory FIFO.
- **SqsCommandBusAdapter** – AWS SQS. Extra: `[sqs]`.
- **RabbitMqCommandBusAdapter** – RabbitMQ. Extra: `[rabbitmq]`.
- **RedisCommandBusAdapter** – Redis Lists. Extra: `[redis]`.

## Response store (ResponseStore)

Implement **`set(key, value, ttl_seconds=60)`**, **`get(key)`**, **`delete(key)`**.

- **InMemoryResponseStore** – In-memory.
- **RedisResponseStore** – Redis. Extra: `[redis]`.

## Interfaces

- **CommandBusAdapter** – Abstract queue contract.
- **CommandBusInterface** – Abstract bus contract.
- **CommandBusRouterInterface** – Abstract router contract.
- **ResponseStore** – Abstract response store contract.
