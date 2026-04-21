"""Declarative multi-bus worker layout for the CLI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .bus import CommandBus


def resolve_bus_attr_on_module(module: object, bus: CommandBus) -> str:
    """
    Find the module-level attribute name that refers to ``bus`` (identity match).

    Worker subprocesses re-import the module and use ``getattr(module, name)``, so each
    bus in a :class:`CommandBusGroup` must be bound to a **top-level** attribute on that
    module. If the same instance is bound under multiple names, the lexicographically
    smallest name is used.
    """
    names = sorted(k for k, v in vars(module).items() if v is bus)
    if not names:
        raise SystemExit(
            "Each CommandBus in a CommandBusGroup must be assigned to a module-level "
            "attribute on the worker module (so the CLI can spawn workers that re-import "
            f"the bus by name). No attribute on {getattr(module, '__name__', module)!r} "
            f"refers to this bus instance: {bus!r}"
        )
    return names[0]


@dataclass(frozen=True)
class WorkerConfig:
    """
    One ``CommandBus`` and how many OS worker processes should consume it.

    Pass the **bus instance** you already constructed. The worker CLI resolves the
    module attribute name for each bus (same object identity on the worker module) so
    child processes can ``import`` the module and ``getattr`` the bus—nothing is pickled.

    If ``workers`` is ``None``, the worker CLI ``--workers`` value is used as the process
    count for this entry.

    **Fork / spawn:** constructing buses at import time is convenient but be careful with
    resources opened before forking (see worker CLI docs).
    """

    bus: CommandBus
    workers: Optional[int] = None


class CommandBusGroup:
    """
    Code-controlled layout for running several ``CommandBus`` instances in one CLI process tree.

    Each entry is a :class:`WorkerConfig` (``bus`` + optional ``workers``). Point the
    worker CLI at ``myapp.worker:command_bus_group`` (or any ``module:attribute`` whose value
    is this group). Otherwise use ``module:bus`` (or ``module`` alone, which defaults the
    attribute to ``bus``) for a single ``CommandBus``.

    Example::

        orders_bus = CommandBus(...)
        priority_bus = CommandBus(...)

        command_bus_group = CommandBusGroup(
            WorkerConfig(orders_bus, workers=4),
            WorkerConfig(priority_bus, workers=2),
        )
    """

    def __init__(self, *configs: WorkerConfig) -> None:
        if not configs:
            raise ValueError("CommandBusGroup requires at least one WorkerConfig")
        self._configs = tuple(configs)

    @property
    def configs(self) -> Tuple[WorkerConfig, ...]:
        return self._configs

    def validate(self, module: object) -> None:
        """Ensure each bus is a ``CommandBus`` and bound to a module-level attribute."""
        for c in self._configs:
            if not isinstance(c.bus, CommandBus):
                raise SystemExit(
                    f"WorkerConfig.bus must be a CommandBus (got {type(c.bus).__name__})"
                )
            resolve_bus_attr_on_module(module, c.bus)

    def iter_jobs(self, module: object, default_workers: int) -> List[Tuple[str, int]]:
        """
        Return ``(bus_attr, worker_index)`` for every worker process to spawn.

        ``default_workers`` is used when a :class:`WorkerConfig` has ``workers=None``.
        """
        if default_workers < 1:
            raise ValueError("default_workers must be >= 1")
        jobs: List[Tuple[str, int]] = []
        for c in self._configs:
            attr = resolve_bus_attr_on_module(module, c.bus)
            n = c.workers if c.workers is not None else default_workers
            if n < 1:
                raise ValueError(f"workers must be >= 1 for {attr!r}, got {n}")
            for w in range(1, n + 1):
                jobs.append((attr, w))
        return jobs
