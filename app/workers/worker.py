from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any

from redis.asyncio import Redis

from app.core.metrics import metrics
from app.core.retry import compute_next_run
from app.core.state_machine import can_transition
from app.db.models import Task, TaskEvent, TaskStatus
from app.db.session import AsyncSessionLocal
from app.queue.locks import RedisLock
from app.queue.redis_queue import RedisQueue
from app.settings import settings

# Ensure task handlers are registered
import app.tasks  # noqa: F401
from app.tasks.registry import get_handler


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def normalize_utc(dt: datetime | None) -> datetime | None:
    """
    SQLite returns naive datetimes. Treat them as UTC.
    """
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def add_event(
    session,
    task_id: str,
    from_status: TaskStatus,
    to_status: TaskStatus,
    message: str,
) -> None:
    session.add(
        TaskEvent(
            task_id=task_id,
            timestamp=now_utc(),
            from_status=from_status.value,
            to_status=to_status.value,
            message=message,
        )
    )


async def run_worker() -> None:
    # 🔥 GUARANTEED VISUAL CONFIRMATION
    print("worker_started", flush=True)

    redis = Redis.from_url(settings.redis_url)
    queue = RedisQueue(redis)
    lock = RedisLock(redis)

    try:
        while True:
            task_id = await queue.dequeue(settings.worker_poll_timeout_seconds)
            if not task_id:
                continue

            acquired = await lock.acquire(task_id)
            if not acquired:
                continue

            start = time.perf_counter()

            try:
                async with AsyncSessionLocal() as session:
                    task = await session.get(Task, task_id)
                    if not task:
                        continue

                    if task.status in {
                        TaskStatus.COMPLETED,
                        TaskStatus.FAILED,
                        TaskStatus.CANCELED,
                    }:
                        continue

                    next_run = normalize_utc(task.next_run_at) or now_utc()
                    if task.status != TaskStatus.QUEUED or next_run > now_utc():
                        continue

                    # Transition → RUNNING
                    if not can_transition(TaskStatus.QUEUED, TaskStatus.RUNNING):
                        continue

                    task.status = TaskStatus.RUNNING
                    task.updated_at = now_utc()
                    await add_event(
                        session,
                        task.id,
                        TaskStatus.QUEUED,
                        TaskStatus.RUNNING,
                        "picked up by worker",
                    )
                    await session.commit()

                    payload = json.loads(task.payload_json)
                    handler = get_handler(task.task_type)

                    try:
                        result = await asyncio.wait_for(handler(payload), timeout=15)

                        task.status = TaskStatus.COMPLETED
                        task.updated_at = now_utc()
                        task.result_json = json.dumps(result)
                        task.last_error = None

                        await add_event(
                            session,
                            task.id,
                            TaskStatus.RUNNING,
                            TaskStatus.COMPLETED,
                            "completed",
                        )
                        await session.commit()
                        await metrics.inc("tasks_completed_total", 1)

                    except Exception as e:
                        task.attempts += 1
                        task.updated_at = now_utc()
                        task.last_error = str(e)

                        if task.attempts >= task.max_attempts:
                            task.status = TaskStatus.FAILED
                            await add_event(
                                session,
                                task.id,
                                TaskStatus.RUNNING,
                                TaskStatus.FAILED,
                                f"failed: {e}",
                            )
                            await metrics.inc("tasks_failed_total", 1)
                        else:
                            task.status = TaskStatus.QUEUED
                            task.next_run_at = compute_next_run(task.attempts)
                            await add_event(
                                session,
                                task.id,
                                TaskStatus.RUNNING,
                                TaskStatus.QUEUED,
                                f"retry scheduled: {e}",
                            )
                            await metrics.inc("tasks_retried_total", 1)

                        await session.commit()

            finally:
                await lock.release(task_id)
                latency_ms = int((time.perf_counter() - start) * 1000)
                print(
                    f"task_processed task_id={task_id} latency_ms={latency_ms}",
                    flush=True,
                )

    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(run_worker())