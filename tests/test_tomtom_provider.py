"""Tests for TomTom live provider (mocked API — no network)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session_factory, reset_engine
from app.providers.errors import ProviderAPIError, ProviderNotConfiguredError
from app.providers.registry import list_providers, reset_provider_registry
from app.providers.scan_limits import effective_scan_limit
from app.providers.tomtom import TomTomProvider
from app.providers.tomtom_parser import parse_tomtom_search_response
from app.services.lead import LeadFilters, list_leads
from app.services.lead_normalization import normalize_provider_record
from app.services.scan import create_scan_job, ensure_default_sources, run_scan_job

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "tomtom"


@pytest.fixture
def geocode_payload() -> dict:
    return json.loads((FIXTURES / "geocode_response.json").read_text(encoding="utf-8"))


@pytest.fixture
def search_payload() -> dict:
    return json.loads((FIXTURES / "search_response.json").read_text(encoding="utf-8"))


@pytest.fixture
def db() -> Session:
    reset_engine()
    reset_provider_registry()
    session = get_session_factory()()
    ensure_default_sources(session)
    yield session
    session.close()
    reset_engine()
    reset_provider_registry()


def test_tomtom_parser_maps_records(search_payload: dict) -> None:
    records = parse_tomtom_search_response(
        search_payload,
        requested_category="barbers",
        requested_city="Charlotte",
        requested_state="NC",
    )
    assert len(records) == 2
    assert records[0].business_name == "Charlotte Barber One"
    assert records[0].external_id == "US/POI/p0/barber-one-charlotte"
    assert records[0].website_url == "https://charlottebarberone.example.com"
    assert records[0].raw_payload["provider"] == "tomtom"


def test_tomtom_normalization_title_cases_city(search_payload: dict) -> None:
    records = parse_tomtom_search_response(
        search_payload,
        requested_category="barbers",
        requested_city="Charlotte",
        requested_state="NC",
    )
    normalized = normalize_provider_record(records[1], "tomtom")
    assert normalized.city == "Charlotte"
    assert normalized.state == "NC"
    assert normalized.phone == "17045550102"


def test_tomtom_provider_search_uses_client(
    geocode_payload: dict,
    search_payload: dict,
) -> None:
    provider = TomTomProvider(
        settings=MagicMock(
            tomtom_api_key="test-key",
            tomtom_timeout_seconds=10,
            tomtom_search_radius_meters=15000,
        )
    )
    with patch.object(provider._client, "geocode", return_value=geocode_payload):
        with patch.object(provider._client, "search_poi", return_value=search_payload) as mock_search:
            result = provider.search_businesses("barbers", "Charlotte", state="NC", limit=25)

    mock_search.assert_called_once()
    assert len(result.records) == 2
    assert result.total == 2


def test_tomtom_missing_api_key_raises() -> None:
    with pytest.raises(ProviderNotConfiguredError):
        TomTomProvider(settings=MagicMock(tomtom_api_key=None, tomtom_timeout_seconds=10))


def test_registry_includes_tomtom_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOMTOM_ENABLED", "true")
    monkeypatch.setenv("TOMTOM_API_KEY", "test-key")
    get_settings.cache_clear()
    reset_provider_registry()

    names = [p.name for p in list_providers()]
    assert "mock" in names
    assert "tomtom" in names
    assert effective_scan_limit("tomtom", 500) == 50
    assert effective_scan_limit("mock", 500) == 500


def test_registry_excludes_tomtom_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOMTOM_ENABLED", "false")
    monkeypatch.delenv("TOMTOM_API_KEY", raising=False)
    get_settings.cache_clear()
    reset_provider_registry()

    assert [p.name for p in list_providers()] == ["mock"]


def test_tomtom_scan_dedup_on_rerun(
    db: Session,
    geocode_payload: dict,
    search_payload: dict,
) -> None:
    city = f"TomTomDedup-{uuid.uuid4().hex[:8]}"
    for i, result in enumerate(search_payload["results"]):
        suffix = uuid.uuid4().hex[:6]
        result["address"]["municipality"] = city
        result["address"]["streetNumber"] = str(9000 + i)
        result["address"]["streetName"] = f"Dedup Ln {suffix}"
        result["poi"]["phone"] = f"+1 999-{suffix[:3]}-{2000 + i}"
        result["poi"]["name"] = f"Dedup Biz {suffix}"
        result["poi"]["url"] = f"https://dedup-{suffix}.example.com"
        result["id"] = f"US/POI/p0/dedup-{suffix}"

    provider = TomTomProvider(
        settings=MagicMock(
            tomtom_api_key="test-key",
            tomtom_timeout_seconds=10,
            tomtom_search_radius_meters=15000,
        )
    )
    with patch.object(provider._client, "geocode", return_value=geocode_payload):
        with patch.object(provider._client, "search_poi", return_value=search_payload):
            with patch("app.services.scan.get_provider", return_value=provider):
                with patch("app.providers.scan_limits.get_provider", return_value=provider):
                    job1 = create_scan_job(db, "barbers", city, "tomtom", "NC")
                    db.commit()
                    run_scan_job(db, job1.id, limit=25)

                    job2 = create_scan_job(db, "barbers", city, "tomtom", "NC")
                    db.commit()
                    run_scan_job(db, job2.id, limit=25)

    assert job1.total_inserted == 2
    assert job2.total_inserted == 0
    assert job2.total_updated == 2
    assert list_leads(db, LeadFilters(city=city)).total == 2


def test_tomtom_api_error_surfaces_in_scan_job(db: Session) -> None:
    provider = TomTomProvider(
        settings=MagicMock(
            tomtom_api_key="test-key",
            tomtom_timeout_seconds=10,
            tomtom_search_radius_meters=15000,
        )
    )
    with patch.object(
        provider._client,
        "geocode",
        side_effect=ProviderAPIError("TomTom API rejected the API key.", status_code=403),
    ):
        with patch("app.services.scan.get_provider", return_value=provider):
            with patch("app.providers.scan_limits.get_provider", return_value=provider):
                job = create_scan_job(db, "salon", "Raleigh", "tomtom", "NC")
                db.commit()
                with pytest.raises(RuntimeError, match="TomTom API rejected"):
                    run_scan_job(db, job.id, limit=10)

    db.refresh(job)
    assert job.status == "failed"
    assert "TomTom API rejected" in (job.error_message or "")
