from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from app.settings import settings


def compute_next_run(attempts: int) -> datetime:
    """
    attempts is the number of failed attempts already recorded (after increment).
    backoff = base * 2^(attempts-1), capped, plus jitter.
    """
    base = settings.retry_base_seconds
    cap = settings.retry_max_seconds
    jitter = settings.retry_jitter_seconds

    delay = min(cap, base * (2 ** max(0, attempts - 1)))
    delay += random.uniform(0, jitter)
    return datetime.now(timezone.utc) + timedelta(seconds=delay)