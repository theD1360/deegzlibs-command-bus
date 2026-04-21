"""Minimal module for CLI integration tests."""

from command_bus import CommandBus
from command_bus.adapters import InMemoryCommandBusAdapter

bus = CommandBus(queue_adapter=InMemoryCommandBusAdapter(queue_name="cli-test"))
