"""Tests for inspection service with mocked HTTP."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.session import get_session_factory, reset_engine
from app.models.business_lead import BusinessLead
from app.models.enums import LeadStatus
from app.providers.base import ProviderRecord
from app.services.inspection_heuristics import HttpFetchResult
from app.services.inspection_service import inspect_lead
from app.services.lead_persistence import upsert_lead
from app.services.scan import ensure_default_sources


class MockFetcher:
    def __init__(self, responses: dict[str, HttpFetchResult]):
        self.responses = responses

    def fetch(self, url: str, timeout_seconds: int) -> HttpFetchResult:
        for key, result in self.responses.items():
            if key in url:
                return result
        return HttpFetchResult(reachable=False, error_message=f"no mock for {url}")


@pytest.fixture
def db() -> Session:
    reset_engine()
    session = get_session_factory()()
    ensure_default_sources(session)
    yield session
    session.close()
    reset_engine()


def _add_lead(db: Session, **kwargs) -> BusinessLead:
    suffix = uuid.uuid4().hex[:8]
    record = ProviderRecord(
        business_name=kwargs.get("business_name", f"Test Biz {suffix}"),
        category="test",
        city=kwargs.get("city", f"TestCity-{suffix}"),
        website_url=kwargs.get("website_url"),
        phone=kwargs.get("phone", f"555{suffix[:7]}"),
        external_id=f"ext-{suffix}",
    )
    lead, _ = upsert_lead(db, record, "mock")
    db.commit()
    return lead


def test_inspect_blank_website(db: Session) -> None:
    lead = _add_lead(db, website_url=None)
    inspection = inspect_lead(db, lead.id, auto_score=False, http_fetcher=MockFetcher({}))
    assert inspection.blank_website is True
    assert inspection.reachable is False


def test_inspect_social_only_skips_fetch(db: Session) -> None:
    lead = _add_lead(db, website_url="https://www.facebook.com/testpage")
    fetcher = MockFetcher({})
    inspection = inspect_lead(db, lead.id, auto_score=False, http_fetcher=fetcher)
    assert inspection.social_only is True
    assert inspection.findings["checks"]  # noqa: SIM118
    assert "social_host_skipped_fetch" in inspection.findings["checks"]
    assert inspection.findings["http_used"] is False


def test_inspect_http_site(db: Session) -> None:
    lead = _add_lead(db, website_url="https://example-local.test")
    html = """
    <html><head><title>Example Co</title>
    <meta name="viewport" content="width=device-width">
    </head><body><a href="/contact">Contact</a></body></html>
    """
    fetcher = MockFetcher(
        {
            "example-local.test": HttpFetchResult(
                final_url="https://example-local.test/",
                http_status=200,
                reachable=True,
                ssl_present=True,
                html=html,
            )
        }
    )
    inspection = inspect_lead(db, lead.id, auto_score=False, http_fetcher=fetcher)
    assert inspection.reachable is True
    assert inspection.branded_domain is True
    assert inspection.has_contact_page is True
    assert inspection.page_title == "Example Co"
    assert inspection.findings["http_used"] is True
