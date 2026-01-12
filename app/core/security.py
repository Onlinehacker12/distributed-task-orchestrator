from __future__ import annotations

from fastapi import Header, HTTPException, Request
from app.settings import settings


async def require_api_key(request: Request, x_api_key: str | None = Header(default=None)) -> None:
    # best-effort request size guard
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.max_request_bytes:
                raise HTTPException(status_code=413, detail="Request too large")
        except ValueError:
            pass

    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")