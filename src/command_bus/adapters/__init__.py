"""Queue and response adapters for the command bus."""

from .queue import (
    FileQueueAdapter,
    InMemoryCommandBusAdapter,
    InMemoryPubSubAdapter,
    SqsCommandBusAdapter,
)

__all__ = [
    "InMemoryCommandBusAdapter",
    "InMemoryPubSubAdapter",
    "SqsCommandBusAdapter",
    "FileQueueAdapter",
]

try:
    from .queue import RabbitMqCommandBusAdapter

    __all__ += ["RabbitMqCommandBusAdapter"]
except ImportError:
    pass

try:
    from .queue import RabbitMqFanoutAdapter

    __all__ += ["RabbitMqFanoutAdapter"]
except ImportError:
    pass

try:
    from .queue import RedisCommandBusAdapter

    __all__ += ["RedisCommandBusAdapter"]
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
