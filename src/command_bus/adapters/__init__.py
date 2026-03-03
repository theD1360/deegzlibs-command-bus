"""Queue and response adapters for the command bus."""

from .queue import FileQueueAdapter, InMemoryCommandBusAdapter, SqsCommandBusAdapter

__all__ = ["InMemoryCommandBusAdapter", "SqsCommandBusAdapter", "FileQueueAdapter"]

try:
    from .queue import RabbitMqCommandBusAdapter

    __all__ += ["RabbitMqCommandBusAdapter"]
except ImportError:
    pass

try:
    from .queue import RedisCommandBusAdapter

    __all__ += ["RedisCommandBusAdapter"]
except ImportError:
    pass

from .response import FileResponseStore, InMemoryResponseStore

__all__ += ["InMemoryResponseStore", "FileResponseStore"]

try:
    from .response import RedisResponseStore

    __all__ += ["RedisResponseStore"]
except ImportError:
    pass
