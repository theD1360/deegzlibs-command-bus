# Installation

## Core package

```bash
pip install deegzlibs-command-bus
```

This gives you the command bus, in-memory queue adapter, in-memory response store, and repr/JSON/Base64 parsers.

It also installs the **`command-bus-worker`** console script for running queue consumers as separate OS processes. See [Worker CLI](cli.md).

## Optional extras

| Extra | Use case |
|-------|----------|
| `[sqs]` | AWS SQS command queue adapter |
| `[sns]` | AWS SNS pub/sub adapter (EventBus fan-out via SQS subscriptions) |
| `[boto3]` | boto3 only (use with SQS or SNS adapters) |
| `[redis]` | Redis queue adapter and Redis response store (for `execute_and_wait`) |
| `[rabbitmq]` | RabbitMQ queue adapter (requires `pika`) |

Examples:

```bash
pip install deegzlibs-command-bus[sqs]
pip install deegzlibs-command-bus[sns]
pip install deegzlibs-command-bus[boto3]
pip install deegzlibs-command-bus[redis]
pip install deegzlibs-command-bus[rabbitmq]
```

Install multiple extras with a comma:

```bash
pip install deegzlibs-command-bus[sqs,sns,redis]
```
