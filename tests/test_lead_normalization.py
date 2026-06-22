"""Tests for provider record normalization."""

from app.providers.base import ProviderRecord
from app.services.lead_normalization import normalize_provider_record


def test_normalize_provider_record() -> None:
    record = ProviderRecord(
        business_name="  Joe's Pizza LLC  ",
        category="restaurant",
        city="Austin",
        state="TX",
        phone="(512) 555-1212",
        address_line1="123 Main St.",
        postal_code="78701",
        website_url="www.example.com",
        external_id="abc123",
        raw_payload={"source": "mock"},
    )
    normalized = normalize_provider_record(record, "mock")

    assert normalized.business_name == "Joe's Pizza LLC"
    assert normalized.normalized_name == "joe s pizza llc"
    assert normalized.phone == "5125551212"
    assert normalized.website_url == "https://www.example.com"
    assert normalized.normalized_domain == "example.com"
    assert normalized.normalized_address_key is not None
    assert normalized.source_name == "mock"
    assert normalized.raw_payload == {"source": "mock"}


def test_normalize_partial_address() -> None:
    record = ProviderRecord(
        business_name="Corner Market",
        category="grocery",
        city="Denver",
        address_line1="3rd & Broadway",
        phone=None,
        website_url=None,
    )
    normalized = normalize_provider_record(record, "mock")
    assert normalized.phone is None
    assert normalized.normalized_address_key is not None
