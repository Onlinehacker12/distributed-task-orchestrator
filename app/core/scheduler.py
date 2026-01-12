from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy import select

from app.db.models import Task, TaskStatus
from app.db.session import AsyncSessionLocal
from app.queue.redis_queue import RedisQueue
from app.settings import settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def scheduler_loop() -> None:
    """
    Periodically scans for tasks that are QUEUED and eligible (next_run_at <= now),
    then enqueues them into Redis for workers to pick up.
    """
    redis = Redis.from_url(settings.redis_url)
    q = RedisQueue(redis)

    try:
        while True:
            async with AsyncSessionLocal() as session:
                stmt = (
                    select(Task)
                    .where(Task.status == TaskStatus.QUEUED, Task.next_run_at <= _now())
                    .order_by(Task.next_run_at.asc())
                    .limit(200)
                )
                res = await session.execute(stmt)
                tasks = list(res.scalars().all())

            for t in tasks:
                await q.enqueue(t.id, priority=t.priority)

            await asyncio.sleep(settings.scheduler_interval_seconds)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(scheduler_loop())