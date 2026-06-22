"""Tests for outreach service."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.session import get_session_factory, reset_engine
from app.models.enums import OutreachDraftStatus
from app.models.website_inspection import WebsiteInspection
from app.providers.base import ProviderRecord
from app.services.lead_persistence import upsert_lead
from app.services.outreach_service import (
    generate_draft,
    list_drafts,
    mark_draft_reviewed,
    regenerate_draft,
)
from app.services.scan import ensure_default_sources


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
        business_name=kwargs.get("business_name", f"Outreach Test {suffix}"),
        category=kwargs.get("category", "salon"),
        city=f"DraftCity-{suffix}",
        website_url=kwargs.get("website_url"),
        phone=f"555{suffix[:7]}",
        external_id=f"or-{suffix}",
    )
    lead, _ = upsert_lead(db, record, "mock")
    db.commit()
    return lead


def test_generate_draft_persists(db: Session) -> None:
    lead = _create_lead(db, website_url=None)
    draft = generate_draft(db, lead.id)
    assert draft.id is not None
    assert draft.subject_line
    assert draft.email_body
    assert draft.short_dm
    assert draft.call_notes
    assert draft.status == OutreachDraftStatus.DRAFT_READY.value
    assert draft.primary_angle == "no_website"
    assert draft.context["findings_used"]


def test_regenerate_creates_new_record(db: Session) -> None:
    lead = _create_lead(db, website_url="https://facebook.com/x")
    first = generate_draft(db, lead.id)
    insp = WebsiteInspection(
        business_lead_id=lead.id,
        social_only=True,
        reachable=True,
        branded_domain=False,
    )
    db.add(insp)
    db.commit()
    second = regenerate_draft(db, lead.id)
    assert second.id != first.id
    assert len(list_drafts(db, lead_id=lead.id)) >= 2


def test_mark_reviewed(db: Session) -> None:
    lead = _create_lead(db, website_url=None)
    draft = generate_draft(db, lead.id)
    updated = mark_draft_reviewed(db, draft.id)
    assert updated.status == OutreachDraftStatus.REVIEWED.value
