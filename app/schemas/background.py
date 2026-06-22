"""Pydantic schemas for background jobs and schedules."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class QueueStatsResponse(BaseModel):
    unified_queue: int
    legacy_inspection_queue: int
    total: int


class EnqueueResponse(BaseModel):
    queued: int = 1
    queue_length: int
    job_id: int | None = None
    mode: str = "queued"


class ScanEnqueueRequest(BaseModel):
    category: str = Field(..., min_length=1, max_length=200)
    city: str = Field(..., min_length=1, max_length=200)
    state: str | None = Field(None, max_length=100)
    source_name: str = Field(default="mock", max_length=100)
    limit: int = Field(default=50, ge=1, le=500)


class BulkInspectionEnqueueRequest(BaseModel):
    lead_ids: list[int] = Field(default_factory=list)
    uninspected_limit: int | None = Field(None, ge=1, le=500)
    auto_score: bool = True


class BulkScoreEnqueueRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=500)


class ExportEnqueueRequest(BaseModel):
    format: str = Field(default="csv")
    filters: dict = Field(default_factory=dict)


class ScheduledTaskCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    task_type: str = Field(..., min_length=1, max_length=50)
    interval_minutes: int = Field(default=60, ge=5, le=10080)
    payload: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class ScheduledTaskUpdateRequest(BaseModel):
    enabled: bool | None = None
    interval_minutes: int | None = Field(None, ge=5, le=10080)
    payload: dict[str, Any] | None = None


class ScheduledTaskResponse(BaseModel):
    id: int
    name: str
    task_type: str
    enabled: bool
    interval_minutes: int
    payload: dict[str, Any] | None
    last_run_at: datetime | None
    next_run_at: datetime | None
    last_status: str | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScheduledTaskListResponse(BaseModel):
    items: list[ScheduledTaskResponse]
    total: int
