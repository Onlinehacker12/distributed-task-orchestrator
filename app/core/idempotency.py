from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Task


async def find_by_idempotency_key(session: AsyncSession, task_type: str, key: str) -> Task | None:
    stmt = select(Task).where(Task.task_type == task_type, Task.idempotency_key == key).limit(1)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()