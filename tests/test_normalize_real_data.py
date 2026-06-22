"""Normalization helpers for messy real-world provider data."""

from app.services.lead_normalization import normalize_provider_record
from app.providers.base import ProviderRecord
from app.utils.normalize import (
    normalize_state,
    partition_website_and_social,
    strip_url_tracking_params,
)


def test_strip_tracking_params_from_url() -> None:
    url = "https://example.com/page?utm_source=google&utm_medium=cpc&id=1"
    cleaned = strip_url_tracking_params(url)
    assert "utm_" not in cleaned
    assert "id=1" in cleaned


def test_social_website_moves_to_social_links() -> None:
    website, social = partition_website_and_social(
        "https://www.facebook.com/mybiz",
        None,
    )
    assert website is None
    assert social["facebook"].startswith("https://")


def test_normalize_provider_record_cleans_messy_phone_and_state() -> None:
    record = ProviderRecord(
        business_name="  Belmont Dental  ",
        category=" Dentists ",
        city="belmont",
        state="nc",
        phone="(704) 555-9999",
        website_url="https://m.example.com?utm_source=tomtom",
        external_id="abc",
        raw_payload={"sample": True},
    )
    normalized = normalize_provider_record(record, "tomtom")
    assert normalized.business_name == "Belmont Dental"
    assert normalized.city == "Belmont"
    assert normalized.state == "NC"
    assert normalized.phone == "7045559999"
    assert "utm_" not in (normalized.website_url or "")


def test_normalize_state_two_letter() -> None:
    assert normalize_state("nc") == "NC"
