"""Worker module with CommandBusGroup for CLI tests."""

from command_bus import CommandBus, CommandBusGroup, WorkerConfig
from command_bus.adapters import InMemoryCommandBusAdapter

orders_bus = CommandBus(queue_adapter=InMemoryCommandBusAdapter(queue_name="orders"))
priority_bus = CommandBus(queue_adapter=InMemoryCommandBusAdapter(queue_name="priority"))

command_bus_group = CommandBusGroup(
    WorkerConfig(orders_bus, workers=2),
    WorkerConfig(priority_bus, workers=1),
)
