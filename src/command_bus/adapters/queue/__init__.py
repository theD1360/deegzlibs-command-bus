"""Queue adapters for the command bus (SQS, RabbitMQ, Redis, in-memory, file, etc.)."""

from .file import FileQueueAdapter
from .in_memory import InMemoryCommandBusAdapter
from .sqs import SqsCommandBusAdapter

__all__ = ["InMemoryCommandBusAdapter", "SqsCommandBusAdapter", "FileQueueAdapter"]

try:
    from .rabbitmq import RabbitMqCommandBusAdapter

    __all__ += ["RabbitMqCommandBusAdapter"]
except ImportError:
    pass

try:
    from .redis import RedisCommandBusAdapter

    __all__ += ["RedisCommandBusAdapter"]
except ImportError:
    pass
