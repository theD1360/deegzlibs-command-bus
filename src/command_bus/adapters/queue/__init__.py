"""Queue adapters for the command bus (SQS, RabbitMQ, Redis, in-memory, file, etc.)."""

from .file import FileQueueAdapter
from .in_memory import InMemoryCommandBusAdapter
from .in_memory_pubsub import InMemoryPubSubAdapter
from .sns_pubsub import SnsPubSubAdapter
from .sqs import SqsCommandBusAdapter

__all__ = [
    "InMemoryCommandBusAdapter",
    "InMemoryPubSubAdapter",
    "SnsPubSubAdapter",
    "SqsCommandBusAdapter",
    "FileQueueAdapter",
]

try:
    from .rabbitmq import RabbitMqCommandBusAdapter

    __all__ += ["RabbitMqCommandBusAdapter"]
except ImportError:
    pass

try:
    from .rabbitmq_fanout import RabbitMqFanoutAdapter

    __all__ += ["RabbitMqFanoutAdapter"]
except ImportError:
    pass

try:
    from .redis import RedisCommandBusAdapter

    __all__ += ["RedisCommandBusAdapter"]
except ImportError:
    pass

try:
    from .redis_pubsub import RedisPubSubAdapter

    __all__ += ["RedisPubSubAdapter"]
except ImportError:
    pass
