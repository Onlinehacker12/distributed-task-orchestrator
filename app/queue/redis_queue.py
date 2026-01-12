from __future__ import annotations

import json
from redis.asyncio import Redis
from app.settings import settings


class RedisQueue:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.key = settings.queue_name

    async def enqueue(self, task_id: str, priority: int = 0) -> None:
        payload = json.dumps({"task_id": task_id, "priority": priority})
        await self.redis.lpush(self.key, payload)

    async def dequeue(self, timeout_seconds: int) -> str | None:
        item = await self.redis.brpop(self.key, timeout=timeout_seconds)
        if not item:
            return None
        _, raw = item
        data = json.loads(raw)
        return data["task_id"]