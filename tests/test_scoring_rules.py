"""Tests for scoring rules and engine."""

from app.models.business_lead import BusinessLead
from app.models.website_inspection import WebsiteInspection
from app.services.scoring_engine import compute_score_breakdown
from app.services.scoring_rules import (
    PRIORITY_HIGH_MIN,
    PRIORITY_MEDIUM_MIN,
    priority_label,
    priority_tier,
)


def _lead(**kwargs) -> BusinessLead:
    return BusinessLead(
        business_name=kwargs.get("business_name", "Test Biz"),
        category=kwargs.get("category", "restaurant"),
        website_url=kwargs.get("website_url"),
        source_name="mock",
        status="new",
    )


def _inspection(**kwargs) -> WebsiteInspection:
    return WebsiteInspection(
        business_lead_id=1,
        blank_website=kwargs.get("blank_website"),
        social_only=kwargs.get("social_only"),
        branded_domain=kwargs.get("branded_domain"),
        reachable=kwargs.get("reachable"),
        ssl_present=kwargs.get("ssl_present"),
        mobile_friendly_basic=kwargs.get("mobile_friendly_basic"),
        has_contact_page=kwargs.get("has_contact_page"),
        has_booking_flow=kwargs.get("has_booking_flow"),
        page_title=kwargs.get("page_title"),
    )


def test_no_website_scoring() -> None:
    breakdown = compute_score_breakdown(_lead(website_url=None), None)
    assert breakdown.no_website_score > 0
    assert breakdown.total_score == breakdown.no_website_score


def test_social_only_scoring() -> None:
    lead = _lead(website_url="https://www.facebook.com/mybiz")
    insp = _inspection(social_only=True, reachable=True)
    breakdown = compute_score_breakdown(lead, insp)
    assert breakdown.social_only_score > 0
    assert breakdown.total_score >= breakdown.social_only_score


def test_branded_vs_weak_domain() -> None:
    branded = compute_score_breakdown(
        _lead(website_url="https://eliteplumbingco.com"),
        _inspection(reachable=True, branded_domain=True, ssl_present=True, page_title="Elite"),
    )
    weak = compute_score_breakdown(
        _lead(website_url="https://mybiz.wixsite.com/menu"),
        _inspection(reachable=True, branded_domain=False, ssl_present=True, page_title="Menu"),
    )
    assert weak.branding_score > branded.branding_score


def test_unreachable_and_no_ssl() -> None:
    breakdown = compute_score_breakdown(
        _lead(website_url="http://example.com"),
        _inspection(reachable=False, ssl_present=False),
    )
    assert breakdown.reachability_score > 0
    assert breakdown.ssl_score > 0


def test_contact_and_booking_for_restaurant() -> None:
    breakdown = compute_score_breakdown(
        _lead(category="restaurant", website_url="https://example.com"),
        _inspection(
            reachable=True,
            ssl_present=True,
            has_contact_page=False,
            has_booking_flow=False,
            page_title="Home",
        ),
    )
    assert breakdown.contact_flow_score >= 20  # contact + booking weights


def test_priority_tiers() -> None:
    assert priority_tier(PRIORITY_HIGH_MIN) == "high"
    assert priority_tier(PRIORITY_MEDIUM_MIN) == "medium"
    assert priority_tier(PRIORITY_MEDIUM_MIN - 1) == "low"
    assert priority_label(PRIORITY_HIGH_MIN) == "High Priority"


def test_scoring_limited_without_inspection() -> None:
    breakdown = compute_score_breakdown(
        _lead(website_url="https://example.com"),
        None,
    )
    assert breakdown.scoring_limited is True
