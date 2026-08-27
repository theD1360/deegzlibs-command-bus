"""Queue adapters for the command bus (SQS, RabbitMQ, Redis, in-memory, file, etc.)."""

from .file import FileQueueAdapter
from .in_memory import InMemoryCommandBusAdapter, InMemoryQueueAdapter
from .in_memory_pubsub import InMemoryPubSubAdapter
from .sns_pubsub import SnsPubSubAdapter
from .sqs import SqsCommandBusAdapter, SqsQueueAdapter

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
    from .rabbitmq import RabbitMqCommandBusAdapter, RabbitMqQueueAdapter

    __all__ += ["RabbitMqQueueAdapter", "RabbitMqCommandBusAdapter"]
except ImportError:
    pass

try:
    from .rabbitmq_fanout import RabbitMqFanoutAdapter

    __all__ += ["RabbitMqFanoutAdapter"]
except ImportError:
    pass

try:
    from .redis import RedisCommandBusAdapter, RedisQueueAdapter

    __all__ += ["RedisQueueAdapter", "RedisCommandBusAdapter"]
except ImportError:
    pass

try:
    from .redis_pubsub import RedisPubSubAdapter

    __all__ += ["RedisPubSubAdapter"]
except ImportError:
    pass
