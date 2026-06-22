"""Tests for scan and lead ingestion services."""

import pytest
from sqlalchemy.orm import Session

from app.db.session import get_session_factory, reset_engine
from app.services.lead import LeadFilters, list_leads
from app.services.scan import create_scan_job, ensure_default_sources, run_scan_job


@pytest.fixture
def db() -> Session:
    reset_engine()
    session = get_session_factory()()
    ensure_default_sources(session)
    yield session
    session.close()
    reset_engine()


def test_run_mock_scan_creates_leads(db: Session) -> None:
    job = create_scan_job(db, "dentist", "Austin", "mock", state="TX")
    db.commit()
    run_scan_job(db, job.id)
    result = list_leads(db, LeadFilters(city="Austin"))
    assert result.total >= 1
    assert any(lead.city == "Austin" for lead in result.leads)


def test_rescan_updates_instead_of_duplicating(db: Session) -> None:
    job1 = create_scan_job(db, "restaurant", "Dallas", "mock", state="TX")
    db.commit()
    run_scan_job(db, job1.id)
    first_count = list_leads(db, LeadFilters(city="Dallas")).total

    job2 = create_scan_job(db, "restaurant", "Dallas", "mock", state="TX")
    db.commit()
    run_scan_job(db, job2.id)
    second_count = list_leads(db, LeadFilters(city="Dallas")).total

    assert first_count == second_count
    assert job2.total_updated >= 1
