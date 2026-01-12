from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


@dataclass
class Metrics:
    tasks_created_total: int = 0
    tasks_completed_total: int = 0
    tasks_failed_total: int = 0
    tasks_retried_total: int = 0
    tasks_canceled_total: int = 0
    worker_exceptions_total: int = 0

    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    async def inc(self, name: str, amount: int = 1) -> None:
        async with self._lock:
            setattr(self, name, getattr(self, name) + amount)

    async def snapshot(self) -> dict:
        async with self._lock:
            return {
                "tasks_created_total": self.tasks_created_total,
                "tasks_completed_total": self.tasks_completed_total,
                "tasks_failed_total": self.tasks_failed_total,
                "tasks_retried_total": self.tasks_retried_total,
                "tasks_canceled_total": self.tasks_canceled_total,
                "worker_exceptions_total": self.worker_exceptions_total,
            }


metrics = Metrics()


def prometheus_text(snapshot: dict) -> str:
    lines = []
    for k, v in snapshot.items():
        lines.append(f"# TYPE {k} counter")
        lines.append(f"{k} {v}")
    return "\n".join(lines) + "\n"