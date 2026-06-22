"""Pydantic schemas for lead API."""

from datetime import datetime

from pydantic import BaseModel


class LeadResponse(BaseModel):
    id: int
    business_name: str
    category: str | None
    city: str | None
    state: str | None
    phone: str | None
    email: str | None
    website_url: str | None
    normalized_domain: str | None
    source_name: str
    external_id: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int
    page: int
    per_page: int
