from fastapi import APIRouter, Depends, Response
from app.core.security import require_api_key
from app.core.metrics import metrics, prometheus_text

router = APIRouter()

@router.get("/v1/metrics", dependencies=[Depends(require_api_key)])
async def get_metrics() -> Response:
    snap = await metrics.snapshot()
    return Response(content=prometheus_text(snap), media_type="text/plain; version=0.0.4")