"""Pydantic schemas for scoring API."""

from datetime import datetime

from pydantic import BaseModel


class ScoreFactorResponse(BaseModel):
    signal: str
    points: int
    detail: str


class ScoreBreakdownResponse(BaseModel):
    total_score: int
    priority_tier: str
    priority_label: str
    scoring_limited: bool = False
    scoring_limited_reason: str | None = None
    factors: list[ScoreFactorResponse]
    sub_scores: dict[str, int]


class LeadScoreResponse(BaseModel):
    id: int
    business_lead_id: int
    scored_at: datetime
    total_score: int
    no_website_score: int
    social_only_score: int
    branding_score: int
    reachability_score: int
    ssl_score: int
    mobile_score: int
    contact_flow_score: int
    outdated_website_score: int
    notes: str | None
    breakdown: ScoreBreakdownResponse | dict | None

    model_config = {"from_attributes": True}


class BulkScoreResponse(BaseModel):
    scored: int | None = None
    rescored: int | None = None
    errors: int
    attempted: int
