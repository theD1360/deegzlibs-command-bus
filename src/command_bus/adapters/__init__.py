"""Queue and response adapters for the command bus."""

from .queue import (
    FileQueueAdapter,
    InMemoryCommandBusAdapter,
    InMemoryPubSubAdapter,
    InMemoryQueueAdapter,
    SnsPubSubAdapter,
    SqsCommandBusAdapter,
    SqsQueueAdapter,
)

__all__ = [
    "InMemoryQueueAdapter",
    "InMemoryCommandBusAdapter",
    "InMemoryPubSubAdapter",
    "SnsPubSubAdapter",
    "SqsQueueAdapter",
    "SqsCommandBusAdapter",
    "FileQueueAdapter",
]

try:
    from .queue import RabbitMqCommandBusAdapter, RabbitMqQueueAdapter

    __all__ += ["RabbitMqQueueAdapter", "RabbitMqCommandBusAdapter"]
except ImportError:
    pass

try:
    from .queue import RabbitMqFanoutAdapter

    __all__ += ["RabbitMqFanoutAdapter"]
except ImportError:
    pass

try:
    from .queue import RedisCommandBusAdapter, RedisQueueAdapter

    __all__ += ["RedisQueueAdapter", "RedisCommandBusAdapter"]
except ImportError:
    pass

try:
    from .queue import RedisPubSubAdapter

    __all__ += ["RedisPubSubAdapter"]
except ImportError:
    pass

from .response import FileResponseStore, InMemoryResponseStore

__all__ += ["InMemoryResponseStore", "FileResponseStore"]

try:
    from .response import RedisResponseStore

    __all__ += ["RedisResponseStore"]
except ImportError:
    pass
