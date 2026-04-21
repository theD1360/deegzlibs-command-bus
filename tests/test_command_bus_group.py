"""Tests for CommandBusGroup and WorkerConfig."""

import sys
import types
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from command_bus import CommandBus, CommandBusGroup, WorkerConfig
from command_bus.adapters import InMemoryCommandBusAdapter


def _sample_module() -> tuple:
    mod = types.ModuleType("testgroup")
    bus_a = CommandBus(queue_adapter=InMemoryCommandBusAdapter(queue_name="qa"))
    bus_b = CommandBus(queue_adapter=InMemoryCommandBusAdapter(queue_name="qb"))
    mod.alpha = bus_a
    mod.beta = bus_b
    return mod, bus_a, bus_b


def test_resolve_bus_attr_on_module():
    from command_bus import resolve_bus_attr_on_module

    mod, bus_a, _ = _sample_module()
    assert resolve_bus_attr_on_module(mod, bus_a) == "alpha"


def test_resolve_bus_attr_picks_lexicographically_first_alias():
    from command_bus import resolve_bus_attr_on_module

    mod = types.ModuleType("aliases")
    bus = CommandBus(queue_adapter=InMemoryCommandBusAdapter(queue_name="q"))
    mod.z_second = bus
    mod.a_first = bus
    assert resolve_bus_attr_on_module(mod, bus) == "a_first"


def test_command_bus_group_iter_jobs():
    mod, bus_a, bus_b = _sample_module()
    g = CommandBusGroup(
        WorkerConfig(bus_a, workers=2),
        WorkerConfig(bus_b, workers=1),
    )
    assert g.iter_jobs(mod, 5) == [("alpha", 1), ("alpha", 2), ("beta", 1)]


def test_command_bus_group_default_workers():
    mod, bus_a, bus_b = _sample_module()
    g = CommandBusGroup(
        WorkerConfig(bus_a, workers=2),
        WorkerConfig(bus_b, workers=None),
    )
    assert g.iter_jobs(mod, 3) == [
        ("alpha", 1),
        ("alpha", 2),
        ("beta", 1),
        ("beta", 2),
        ("beta", 3),
    ]


def test_command_bus_group_empty_raises():
    with pytest.raises(ValueError, match="at least one"):
        CommandBusGroup()


def test_command_bus_group_validate():
    from tests.support import cli_group_worker_module

    cli_group_worker_module.command_bus_group.validate(cli_group_worker_module)


def test_iter_jobs_workers_zero_raises():
    mod, bus_a, _ = _sample_module()
    g = CommandBusGroup(WorkerConfig(bus_a, workers=0))
    with pytest.raises(ValueError, match=">= 1"):
        g.iter_jobs(mod, default_workers=1)


def test_bus_not_bound_to_module_raises():
    mod = types.ModuleType("orphan")
    bus = CommandBus(queue_adapter=InMemoryCommandBusAdapter(queue_name="x"))
    g = CommandBusGroup(WorkerConfig(bus))
    with pytest.raises(SystemExit, match="module-level"):
        g.validate(mod)
