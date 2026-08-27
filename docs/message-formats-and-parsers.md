# Message formats and parsers

When the bus dispatches a message (e.g. in `work()`), it receives a raw string from the queue adapter. A **message parser** turns that string into a `CommandMessage` instance so the router can find handlers and call them.

The parser is configured on the **bus** when you create it (not on the adapter). Default is **repr-style** strings.

## Default format: repr-style

The default parser expects strings like:

```text
module.path.ClassName(arg1, arg2, kw=val)
```

Example: `tests.my_commands.OrderCreated(order_id='ord-1', amount_cents=1999)`.

- **`MessageParser`** (alias for **`ReprMessageParser`**) – Parses these strings. Supports literals, `None`, `True`, `False`, nested structures, and class constructors from the same or other modules.
- `str(message)` on a `CommandMessage` produces this format, so enqueued messages are parser-compatible.

## Setting the parser on the bus

Pass **`message_parser_class`** when creating the bus. If you omit it, **`ReprMessageParser`** is used.

```python
from command_bus import CommandBus, Router
from command_bus.adapters import SqsQueueAdapter
from command_bus.parsers import JsonMessageParser

adapter = SqsQueueAdapter(queue_name="my-commands", sqs_client=sqs)
router = Router()
bus = CommandBus(
    queue_adapter=adapter,
    command_router=router,
    message_parser_class=JsonMessageParser,
)
```

## Built-in parsers

| Parser | Format | Notes |
|--------|--------|--------|
| **ReprMessageParser** (exported as **MessageParser**) | `module.ClassName(...)` repr-style | Default. |
| **JsonMessageParser** | JSON object | Expects a type field (default `"__type__"`) with the fully qualified message class name; remaining keys are kwargs for that class. Use `JsonMessageParser(json_str, type_key="type")` to change the type key. Optional **`MessageCodec`** wraps the JSON string (base64, gzip, or chained). Serialize with **`JsonMessageParser.dumps(message, codec=...)`**. |
| **Base64MessageParser** | Base64-encoded payload | Decodes then parses with an inner parser. Optional gzip: `Base64MessageParser(encoded, decompress=True)`. For base64 JSON: `Base64MessageParser(encoded, inner_parser_class=JsonMessageParser)`. |
| **MessageCodec** | Wrapper layer | Optional encode/decode around JSON (or other string payloads). Built-ins: **`Base64MessageCodec`**, **`GzipMessageCodec`**, **`ChainedMessageCodec`**. Use **`configure_json_parser(codec=...)`** as `message_parser_class` on the bus. |

## JSON with codecs

Wrap JSON payloads for transport (e.g. gzip then base64):

```python
from command_bus import CommandBus, Router
from command_bus.parsers import (
    Base64MessageCodec,
    ChainedMessageCodec,
    GzipMessageCodec,
    JsonMessageParser,
    configure_json_parser,
)

codec = ChainedMessageCodec([GzipMessageCodec(), Base64MessageCodec()])
bus = CommandBus(
    queue_adapter=adapter,
    command_router=router,
    message_parser_class=configure_json_parser(codec=codec),
)

# Producer: serialize with the same codec before enqueue
body = JsonMessageParser.dumps(my_command, codec=codec)
```

Implement **`MessageCodec`** for custom wrappers: **`encode(payload: str) -> str`** and **`decode(wrapped: str) -> str`**.

## Custom format

Implement **`MessageParserBase`** from `command_bus.parsers`:

- **`initialize() -> TransmissibleBaseModel`** – Parse a raw string into a message instance.
- **`dumps(message) -> str`** – Serialize for transport (default: repr-style `str(message)`).
- **`subject(message, encoded_body) -> str | None`** – Optional publish subject (e.g. event type).
- **`message_attributes(message, encoded_body) -> dict | None`** – Optional publish message attributes.

Pass your class as **`message_parser_class`** when creating the bus.
