from datetime import datetime, timezone
from app.core.retry import compute_next_run


def test_retry_backoff_returns_future_time():
    now = datetime.now(timezone.utc)
    n1 = compute_next_run(1)
    n2 = compute_next_run(2)
    assert n1 > now
    assert n2 > now