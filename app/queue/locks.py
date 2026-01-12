from __future__ import annotations

from redis.asyncio import Redis
from app.settings import settings


class RedisLock:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def acquire(self, task_id: str) -> bool:
        key = f"dto:lock:{task_id}"
        return bool(await self.redis.set(key, "1", nx=True, ex=settings.task_lock_ttl_seconds))

    async def release(self, task_id: str) -> None:
        key = f"dto:lock:{task_id}"
        await self.redis.delete(key)