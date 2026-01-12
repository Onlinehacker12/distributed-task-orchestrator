from __future__ import annotations

from typing import Awaitable, Callable

TaskHandler = Callable[[dict], Awaitable[dict]]

_registry: dict[str, TaskHandler] = {}


def register(task_type: str):
    def _decorator(fn: TaskHandler) -> TaskHandler:
        _registry[task_type] = fn
        return fn
    return _decorator


def get_handler(task_type: str) -> TaskHandler:
    if task_type not in _registry:
        raise KeyError(f"Unknown task_type: {task_type}")
    return _registry[task_type]


def registered_task_types() -> list[str]:
    return sorted(_registry.keys())