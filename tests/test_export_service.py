"""Tests for export service."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.session import get_session_factory, reset_engine
from app.models.enums import ExportJobStatus
from app.models.lead_score import LeadScore
from app.models.website_inspection import WebsiteInspection
from app.providers.base import ProviderRecord
from app.services.export_service import (
    create_export_job,
    lead_filters_from_dict,
    run_export_job,
    write_leads_csv,
)
from app.services.lead_persistence import upsert_lead
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
        business_name=kwargs.get("business_name", f"Export Test {suffix}"),
        category=kwargs.get("category", "plumber"),
        city=kwargs.get("city", f"ExportCity-{suffix}"),
        website_url=kwargs.get("website_url"),
        phone=f"555{suffix[:7]}",
        external_id=f"ex-{suffix}",
    )
    lead, _ = upsert_lead(db, record, "mock")
    db.commit()
    return lead


def test_run_export_job_completes(db: Session, tmp_path) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    settings.export_dir = tmp_path

    lead = _create_lead(db, website_url=None)
    db.add(
        LeadScore(
            business_lead_id=lead.id,
            total_score=40,
            no_website_score=35,
            social_only_score=0,
            branding_score=0,
            contact_flow_score=0,
            mobile_score=0,
            outdated_website_score=0,
            reachability_score=0,
            ssl_score=0,
        )
    )
    db.commit()

    job = create_export_job(db, {"city": lead.city})
    db.commit()
    completed = run_export_job(db, job.id, settings=settings)
    assert completed.status == ExportJobStatus.COMPLETED.value
    assert completed.row_count == 1
    content = (tmp_path / completed.file_path).read_text(encoding="utf-8")
    assert "lead_id" in content
    assert lead.business_name in content


def test_export_filter_by_priority(db: Session, tmp_path) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    settings.export_dir = tmp_path

    suffix = uuid.uuid4().hex[:8]
    city = f"PriorityCity-{suffix}"
    high = _create_lead(db, business_name="High Priority Biz", city=city)
    low = _create_lead(db, business_name="Low Priority Biz", city=city)
    db.add(LeadScore(business_lead_id=high.id, total_score=60, no_website_score=35, social_only_score=0, branding_score=0, contact_flow_score=0, mobile_score=0, outdated_website_score=0, reachability_score=0, ssl_score=0))
    db.add(LeadScore(business_lead_id=low.id, total_score=10, no_website_score=0, social_only_score=0, branding_score=0, contact_flow_score=0, mobile_score=0, outdated_website_score=0, reachability_score=0, ssl_score=0))
    db.commit()

    job = create_export_job(db, {"city": city, "priority": "high"})
    db.commit()
    completed = run_export_job(db, job.id, settings=settings)
    assert completed.row_count == 1
    content = (tmp_path / completed.file_path).read_text(encoding="utf-8")
    assert "High Priority Biz" in content
    assert "Low Priority Biz" not in content


def test_lead_filters_from_dict() -> None:
    filters = lead_filters_from_dict({"city": "Austin", "min_score": "25", "priority": "high"})
    assert filters.city == "Austin"
    assert filters.min_score == 25
    assert filters.priority == "high"
