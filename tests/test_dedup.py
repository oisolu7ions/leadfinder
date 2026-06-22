"""Tests for lead deduplication behavior."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.session import get_session_factory, reset_engine
from app.providers.base import ProviderRecord
from app.services.lead import LeadFilters, list_leads
from app.services.lead_persistence import upsert_lead
from app.services.scan import create_scan_job, ensure_default_sources, run_scan_job


@pytest.fixture
def db() -> Session:
    reset_engine()
    session = get_session_factory()()
    ensure_default_sources(session)
    yield session
    session.close()
    reset_engine()


def test_address_dedup_matches_street_variants(db: Session) -> None:
    city = f"DedupTestVille-{uuid.uuid4().hex[:8]}"
    phone_base = int(uuid.uuid4().int % 9000000) + 1000000
    first, inserted = upsert_lead(
        db,
        ProviderRecord(
            business_name="Main St Dental",
            category="dentist",
            city=city,
            state="TX",
            address_line1="101 Main St",
            postal_code="78701",
            phone=str(phone_base),
            external_id=f"ext-a-{uuid.uuid4().hex[:8]}",
        ),
        "mock",
    )
    assert inserted is True

    second, inserted = upsert_lead(
        db,
        ProviderRecord(
            business_name="Main Street Dental",
            category="dentist",
            city=city,
            state="TX",
            address_line1="101 Main Street",
            postal_code="78701",
            phone=str(phone_base + 1),
            external_id=f"ext-b-{uuid.uuid4().hex[:8]}",
        ),
        "mock",
    )
    db.commit()

    assert inserted is False
    assert second.id == first.id


def test_mock_duplicate_dental_not_duplicated(db: Session) -> None:
    job = create_scan_job(db, "dentist", "Memphis", "mock", state="TN")
    db.commit()
    run_scan_job(db, job.id, limit=50)
    result = list_leads(db, LeadFilters(city="Memphis"))
    dental = [lead for lead in result.leads if "Dental" in lead.business_name]
    assert len(dental) == 1
    assert job.total_inserted + job.total_updated >= 1
