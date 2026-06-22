"""Pydantic schemas for outreach draft API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class OutreachDraftResponse(BaseModel):
    id: int
    business_lead_id: int
    created_at: datetime
    tone: str
    subject_line: str | None
    email_body: str | None
    short_dm: str | None
    call_notes: str | None
    status: str
    primary_angle: str | None = None
    context: dict | None = None

    model_config = {"from_attributes": True}


class OutreachDraftListResponse(BaseModel):
    items: list[OutreachDraftResponse]
    total: int


class OutreachDraftStatusUpdate(BaseModel):
    status: str = Field(description="draft_ready | reviewed | archived")


class OutreachGenerateResponse(BaseModel):
    draft: OutreachDraftResponse
    message: str = "Draft created for review — not sent."
