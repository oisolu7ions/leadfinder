"""Tests for inspection heuristics (no network)."""

from app.services.inspection_heuristics import (
    analyze_html,
    is_google_business_url,
    is_social_or_directory_url,
    run_prechecks,
)


def test_blank_website_precheck() -> None:
    result = run_prechecks(None)
    assert result.blank_website is True
    assert "blank_website" in result.checks


def test_social_only_facebook() -> None:
    result = run_prechecks("https://www.facebook.com/mybiz")
    assert result.social_only is True
    assert result.branded_domain is False


def test_branded_domain() -> None:
    result = run_prechecks("https://www.eliteplumbingco.com")
    assert result.social_only is False
    assert result.branded_domain is True


def test_free_subdomain_not_branded() -> None:
    result = run_prechecks("https://mybiz.wixsite.com/menu")
    assert result.branded_domain is False


def test_google_business_url() -> None:
    assert is_google_business_url("https://maps.google.com/maps?q=test", None) is True
    assert is_social_or_directory_url("https://maps.google.com/maps?q=test", "google.com") is True


def test_analyze_html_contact_and_booking() -> None:
    html = """
    <html><head>
    <title>Joe's Plumbing</title>
    <meta name="viewport" content="width=device-width">
    <meta name="description" content="We fix pipes">
    </head><body>
    <a href="/contact">Contact us</a>
    <button>Book appointment online</button>
    </body></html>
    """
    analysis = analyze_html(html)
    assert analysis.page_title == "Joe's Plumbing"
    assert analysis.has_contact_page is True
    assert analysis.has_booking_flow is True
    assert analysis.mobile_friendly_basic is True
