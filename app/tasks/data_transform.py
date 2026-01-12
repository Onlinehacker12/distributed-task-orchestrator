from __future__ import annotations

from app.tasks.registry import register


@register("data_transform")
async def data_transform(payload: dict) -> dict:
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("payload.data must be an object")

    select = payload.get("select")
    if select is not None and (not isinstance(select, list) or not all(isinstance(x, str) for x in select)):
        raise ValueError("payload.select must be a list of strings")

    rename = payload.get("rename")
    if rename is not None and (
        not isinstance(rename, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in rename.items())
    ):
        raise ValueError("payload.rename must be a string->string map")

    out = dict(data)

    if select is not None:
        out = {k: out.get(k) for k in select}

    if rename:
        out = {rename.get(k, k): v for k, v in out.items()}

    return {"transformed": out, "field_count": len(out)}