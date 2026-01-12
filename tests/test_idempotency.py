import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.idempotency import find_by_idempotency_key
from app.db.models import Base, Task, TaskStatus


@pytest.mark.asyncio
async def test_find_by_idempotency_key():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        tid = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        t = Task(
            id=tid,
            task_type="cpu_burn",
            payload_json=json.dumps({"milliseconds": 10}),
            status=TaskStatus.QUEUED,
            priority=0,
            idempotency_key="k1",
            attempts=0,
            max_attempts=5,
            created_at=now,
            updated_at=now,
            next_run_at=now,
            locked_until=None,
            last_error=None,
            result_json=None,
        )
        session.add(t)
        await session.commit()

        found = await find_by_idempotency_key(session, "cpu_burn", "k1")
        assert found is not None
        assert found.id == tid