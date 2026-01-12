from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class TaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_type: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any]
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=128)
    priority: int | None = Field(default=None, ge=-100, le=100)


class TaskResponse(BaseModel):
    id: str
    task_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    next_run_at: datetime
    attempts: int
    max_attempts: int
    priority: int
    last_error: str | None
    result: dict[str, Any] | None
    idempotency_key: str | None


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    next_cursor: str | None


class CancelResponse(BaseModel):
    id: str
    status: Literal["CANCELED"]