from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from app.core.security import require_api_key
from app.settings import settings

router = APIRouter()

@router.get("/v1/health", dependencies=[Depends(require_api_key)])
async def health(redis: Redis = Depends(lambda: Redis.from_url(settings.redis_url))) -> dict:
    pong = await redis.ping()
    return {"ok": True, "redis": bool(pong)}