"""Pydantic schemas for inspection API."""

from datetime import datetime

from pydantic import BaseModel


class InspectionResponse(BaseModel):
    id: int
    business_lead_id: int
    inspected_at: datetime | None
    final_url: str | None
    http_status: int | None
    reachable: bool | None
    blank_website: bool | None
    social_only: bool | None
    branded_domain: bool | None
    mobile_friendly_basic: bool | None
    has_contact_page: bool | None
    has_booking_flow: bool | None
    ssl_present: bool | None
    page_title: str | None
    meta_description: str | None
    screenshot_path: str | None
    html_snapshot_path: str | None
    findings: dict | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InspectionListResponse(BaseModel):
    items: list[InspectionResponse]
    total: int


class InspectionQueueRequest(BaseModel):
    lead_ids: list[int] | None = None
    uninspected_limit: int | None = None


class InspectionQueueResponse(BaseModel):
    queued: int
    queue_length: int


class InspectionRunRequest(BaseModel):
    run_browser: bool | None = None
    auto_score: bool = True
