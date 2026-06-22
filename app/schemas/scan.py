"""Pydantic schemas for scan job API."""

from datetime import datetime

from pydantic import BaseModel, Field


class ScanCreateRequest(BaseModel):
    category: str = Field(..., min_length=1, max_length=200)
    city: str = Field(..., min_length=1, max_length=200)
    state: str | None = Field(None, max_length=100)
    source_name: str = Field(default="mock", max_length=100)
    limit: int = Field(default=50, ge=1, le=500)
    page: int = Field(default=1, ge=1)
    run_immediately: bool = Field(default=True)


class ScanJobResponse(BaseModel):
    id: int
    category: str
    city: str
    state: str | None
    query_text: str | None
    source_name: str
    status: str
    total_found: int
    total_inserted: int
    total_updated: int
    total_flagged: int
    error_message: str | None
    logs_summary: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScanJobListResponse(BaseModel):
    items: list[ScanJobResponse]
    total: int
