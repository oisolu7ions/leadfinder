"""Pydantic schemas for export API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ExportCreateRequest(BaseModel):
    format: str = Field(default="csv")
    filters: dict = Field(default_factory=dict)
    run_immediately: bool = Field(default=True)


class ExportJobResponse(BaseModel):
    id: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    format: str
    filters: dict | None
    filters_summary: str
    file_path: str | None
    status: str
    error_message: str | None
    row_count: int | None = None

    model_config = {"from_attributes": True}


class ExportJobListResponse(BaseModel):
    items: list[ExportJobResponse]
    total: int
