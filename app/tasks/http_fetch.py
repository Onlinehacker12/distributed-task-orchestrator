from __future__ import annotations

import ipaddress
import time
from urllib.parse import urlparse

import httpx
from app.tasks.registry import register


def _is_private_host(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        lowered = host.lower()
        return lowered == "localhost" or lowered.endswith(".local")


@register("http_fetch")
async def http_fetch(payload: dict) -> dict:
    url = payload.get("url")
    if not isinstance(url, str) or not url:
        raise ValueError("payload.url is required")

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http/https URLs are allowed")
    if not parsed.hostname:
        raise ValueError("URL hostname missing")
    if _is_private_host(parsed.hostname):
        raise ValueError("Private/localhost targets are blocked")

    timeout = float(payload.get("timeout_seconds", 5.0))
    timeout = max(0.5, min(timeout, 10.0))

    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        r = await client.get(url)
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    return {"status_code": r.status_code, "latency_ms": elapsed_ms}