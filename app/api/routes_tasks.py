from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import CancelResponse, TaskCreateRequest, TaskListResponse, TaskResponse
from app.core.idempotency import find_by_idempotency_key
from app.core.metrics import metrics
from app.core.security import require_api_key
from app.core.state_machine import can_transition
from app.db.models import Task, TaskEvent, TaskStatus
from app.db.session import AsyncSessionLocal
from app.queue.redis_queue import RedisQueue
from app.settings import settings

router = APIRouter()


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def get_redis() -> Redis:
    r = Redis.from_url(settings.redis_url)
    try:
        yield r
    finally:
        await r.aclose()


def _task_to_response(t: Task) -> TaskResponse:
    result = json.loads(t.result_json) if t.result_json else None
    return TaskResponse(
        id=t.id,
        task_type=t.task_type,
        status=t.status.value if hasattr(t.status, "value") else str(t.status),
        created_at=t.created_at,
        updated_at=t.updated_at,
        next_run_at=t.next_run_at,
        attempts=t.attempts,
        max_attempts=t.max_attempts,
        priority=t.priority,
        last_error=t.last_error,
        result=result,
        idempotency_key=t.idempotency_key,
    )


def _encode_cursor(dt: datetime, task_id: str) -> str:
    raw = f"{dt.isoformat()}|{task_id}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
        dt_s, tid = raw.split("|", 1)
        return datetime.fromisoformat(dt_s), tid
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid cursor") from e


async def _event(session: AsyncSession, task_id: str, from_s: TaskStatus, to_s: TaskStatus, msg: str) -> None:
    session.add(
        TaskEvent(
            task_id=task_id,
            timestamp=_now(),
            from_status=from_s.value,
            to_status=to_s.value,
            message=msg,
        )
    )


@router.post("/v1/tasks", dependencies=[Depends(require_api_key)], response_model=TaskResponse)
async def create_task(
    req: TaskCreateRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> TaskResponse:
    # Ensure task handlers are registered (import side effects)
    import app.tasks  # noqa: F401

    # Idempotency: if same key used, return existing task
    if req.idempotency_key:
        existing = await find_by_idempotency_key(session, req.task_type, req.idempotency_key)
        if existing:
            return _task_to_response(existing)

    tid = str(uuid.uuid4())
    now = _now()

    t = Task(
        id=tid,
        task_type=req.task_type,
        payload_json=json.dumps(req.payload),
        status=TaskStatus.PENDING,
        priority=req.priority or 0,
        idempotency_key=req.idempotency_key,
        attempts=0,
        max_attempts=settings.default_max_attempts,
        created_at=now,
        updated_at=now,
        next_run_at=now,
        locked_until=None,
        last_error=None,
        result_json=None,
    )
    session.add(t)
    await _event(session, t.id, TaskStatus.PENDING, TaskStatus.PENDING, "created")

    # Transition to QUEUED + enqueue
    if not can_transition(TaskStatus.PENDING, TaskStatus.QUEUED):
        raise HTTPException(status_code=500, detail="Invalid state transition (PENDING->QUEUED)")

    t.status = TaskStatus.QUEUED
    t.updated_at = _now()
    await _event(session, t.id, TaskStatus.PENDING, TaskStatus.QUEUED, "enqueued")
    await session.commit()

    q = RedisQueue(redis)
    await q.enqueue(t.id, priority=t.priority)

    await metrics.inc("tasks_created_total", 1)
    return _task_to_response(t)


@router.get("/v1/tasks/{task_id}", dependencies=[Depends(require_api_key)], response_model=TaskResponse)
async def get_task(task_id: str, session: AsyncSession = Depends(get_session)) -> TaskResponse:
    t = await session.get(Task, task_id)
    if not t:
        raise HTTPException(status_code=404, detail="Not found")
    return _task_to_response(t)


@router.get("/v1/tasks", dependencies=[Depends(require_api_key)], response_model=TaskListResponse)
async def list_tasks(
    status: str | None = None,
    limit: int = 20,
    cursor: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> TaskListResponse:
    limit = max(1, min(limit, 100))
    filters = []

    if status:
        try:
            st = TaskStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
        filters.append(Task.status == st)

    stmt = select(Task)
    if filters:
        stmt = stmt.where(and_(*filters))

    # Cursor pagination: created_at desc, id desc
    stmt = stmt.order_by(Task.created_at.desc(), Task.id.desc())

    if cursor:
        dt, tid = _decode_cursor(cursor)
        stmt = stmt.where(
            or_(
                Task.created_at < dt,
                and_(Task.created_at == dt, Task.id < tid),
            )
        )

    stmt = stmt.limit(limit + 1)
    res = await session.execute(stmt)
    rows = list(res.scalars().all())

    next_cursor = None
    if len(rows) > limit:
        last = rows[limit - 1]
        next_cursor = _encode_cursor(last.created_at, last.id)
        rows = rows[:limit]

    return TaskListResponse(items=[_task_to_response(t) for t in rows], next_cursor=next_cursor)


@router.post("/v1/tasks/{task_id}/cancel", dependencies=[Depends(require_api_key)], response_model=CancelResponse)
async def cancel_task(task_id: str, session: AsyncSession = Depends(get_session)) -> CancelResponse:
    t = await session.get(Task, task_id)
    if not t:
        raise HTTPException(status_code=404, detail="Not found")

    if t.status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED}:
        raise HTTPException(status_code=409, detail="Task is terminal")

    from_s = t.status
    t.status = TaskStatus.CANCELED
    t.updated_at = _now()
    await _event(session, t.id, from_s, TaskStatus.CANCELED, "canceled via API")
    await session.commit()

    await metrics.inc("tasks_canceled_total", 1)
    return CancelResponse(id=t.id, status="CANCELED")