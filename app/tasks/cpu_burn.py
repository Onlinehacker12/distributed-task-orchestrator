from __future__ import annotations

import time
from app.tasks.registry import register


@register("cpu_burn")
async def cpu_burn(payload: dict) -> dict:
    ms = payload.get("milliseconds")
    if not isinstance(ms, int):
        raise ValueError("payload.milliseconds must be an integer")
    ms = max(1, min(ms, 500))

    end = time.perf_counter() + (ms / 1000.0)
    x = 0
    while time.perf_counter() < end:
        x = (x * 31 + 7) % 1_000_000_007

    return {"burned_ms": ms, "checksum": x}