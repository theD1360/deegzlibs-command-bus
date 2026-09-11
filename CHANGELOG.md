# Changelog

## 3.0.0

### Breaking

- **`RedisQueueAdapter`** now uses **Redis Streams** + consumer groups instead of Lists (`LPUSH`/`BRPOP`).
  - Existing list keys are not compatible (`WRONGTYPE`); migrate with **`migrate_redis_list_to_stream`** or drain and use a new key.
  - Requires **Redis ≥ 6.2** for `XAUTOCLAIM` reclaim.
  - Delivery is **at-least-once**; handlers must be idempotent.

### Added

- Real **`visibility_timeout`** / **`default_visibility_timeout`** on Redis (claim idle pending via `XAUTOCLAIM`).
- **`ReleaseMessage`** — raise from handler/middleware so `work()` skips ack; message can reappear after visibility timeout.
- **`migrate_redis_list_to_stream(redis_client, list_key, stream_key=None)`** migration helper.
- Docs: Redis Streams semantics, ack policy table, WorkerApp as the standard worker path.

### Fixed

- **`queue_admin`** no longer hard-imports RabbitMQ/`pika` (optional `[rabbitmq]` extra).

### Unchanged

- Default **always-ack** on handler/middleware failure (except `ReleaseMessage`).
- WorkerApp / lifecycle / middleware onion shape.
- SQS, File, RabbitMQ, InMemory adapter behavior (aside from shared `ReleaseMessage` support in `work()`).
