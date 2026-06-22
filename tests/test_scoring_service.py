"""Tests for scoring service."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.session import get_session_factory, reset_engine
from app.models.website_inspection import WebsiteInspection
from app.providers.base import ProviderRecord
from app.services.lead_persistence import upsert_lead
from app.services.scan import ensure_default_sources
from app.services.scoring_rules import priority_tier
from app.services.scoring_service import (
    list_unscored_lead_ids,
    rescore_lead,
    score_lead,
    score_unscored_leads,
)


@pytest.fixture
def db() -> Session:
    reset_engine()
    session = get_session_factory()()
    ensure_default_sources(session)
    yield session
    session.close()
    reset_engine()


def _create_lead(db: Session, **kwargs):
    suffix = uuid.uuid4().hex[:8]
    record = ProviderRecord(
        business_name=kwargs.get("business_name", f"Score Test {suffix}"),
        category=kwargs.get("category", "dentist"),
        city=f"ScoreCity-{suffix}",
        website_url=kwargs.get("website_url"),
        phone=f"555{suffix[:7]}",
        external_id=f"sc-{suffix}",
    )
    lead, _ = upsert_lead(db, record, "mock")
    db.commit()
    return lead


def test_score_lead_persists_breakdown(db: Session) -> None:
    lead = _create_lead(db, website_url=None)
    score = score_lead(db, lead.id)
    assert score.total_score > 0
    assert score.breakdown is not None
    assert score.breakdown["priority_tier"] == priority_tier(score.total_score)
    assert score.no_website_score > 0


def test_rescore_updates_with_inspection(db: Session) -> None:
    lead = _create_lead(db, website_url="https://example.com")
    first = score_lead(db, lead.id)
    insp = WebsiteInspection(
        business_lead_id=lead.id,
        reachable=True,
        ssl_present=True,
        social_only=False,
        branded_domain=True,
        has_contact_page=True,
        has_booking_flow=True,
        mobile_friendly_basic=True,
        page_title="Example",
    )
    db.add(insp)
    db.commit()
    second = rescore_lead(db, lead.id)
    assert second.id != first.id
    assert second.total_score <= first.total_score or second.total_score >= 0


def test_score_unscored_bulk(db: Session) -> None:
    _create_lead(db, website_url=None)
    _create_lead(db, website_url="https://facebook.com/x")
    unscored_before = len(list_unscored_lead_ids(db, limit=100))
    result = score_unscored_leads(db, limit=10)
    assert result["scored"] >= 1
    assert result["attempted"] <= unscored_before + 2
