"""Tests for normalization utilities."""

from app.utils.normalize import (
    extract_domain,
    is_free_subdomain,
    is_social_host,
    normalize_business_name,
    normalize_phone,
)


def test_normalize_business_name() -> None:
    assert normalize_business_name("Joe's Pizza & Grill") == "joe s pizza grill"


def test_normalize_phone() -> None:
    assert normalize_phone("(555) 010-1234") == "5550101234"


def test_extract_domain() -> None:
    assert extract_domain("https://www.example.com/page") == "example.com"


def test_social_host_detection() -> None:
    assert is_social_host("facebook.com") is True
    assert is_social_host("example.com") is False


def test_free_subdomain_detection() -> None:
    assert is_free_subdomain("mybiz.wixsite.com") is True
    assert is_free_subdomain("example.com") is False


def test_address_dedup_key_matches_variants() -> None:
    from app.utils.normalize import address_dedup_key

    key_a = address_dedup_key("101 Main St.", "Austin", "TX", "78701")
    key_b = address_dedup_key("101 Main Street", "Austin", "TX", "78701")
    assert key_a == key_b
