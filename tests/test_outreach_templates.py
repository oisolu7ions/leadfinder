"""Tests for outreach template selection and rendering."""

from app.models.business_lead import BusinessLead
from app.models.website_inspection import WebsiteInspection
from app.services.outreach_templates import detect_findings, render_draft


def _lead(**kwargs) -> BusinessLead:
    return BusinessLead(
        id=kwargs.get("id", 1),
        business_name=kwargs.get("business_name", "Test Cafe"),
        category=kwargs.get("category", "cafe"),
        city=kwargs.get("city", "Portland"),
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
        has_contact_page=kwargs.get("has_contact_page"),
        has_booking_flow=kwargs.get("has_booking_flow"),
        mobile_friendly_basic=kwargs.get("mobile_friendly_basic"),
    )


def test_no_website_draft_angle() -> None:
    findings = detect_findings(_lead(website_url=None), None, None)
    assert findings[0].angle == "no_website"
    draft = render_draft(_lead(website_url=None), None, None)
    assert draft.primary_angle == "no_website"
    assert "No dedicated business website" in draft.email_body
    assert draft.subject_line
    assert draft.short_dm
    assert draft.call_notes


def test_social_only_draft_angle() -> None:
    lead = _lead(website_url="https://facebook.com/mybiz")
    insp = _inspection(social_only=True, reachable=True)
    draft = render_draft(lead, insp, None)
    assert draft.primary_angle == "social_only"
    assert "social" in draft.email_body.lower()


def test_weak_branding_draft() -> None:
    lead = _lead(website_url="https://mybiz.wixsite.com/home")
    insp = _inspection(branded_domain=False, reachable=True, has_contact_page=True)
    draft = render_draft(lead, insp, None)
    assert draft.primary_angle == "weak_branding"
    assert "branded" in draft.email_body.lower() or "subdomain" in draft.findings_used[0].lower()


def test_missing_booking_for_restaurant() -> None:
    lead = _lead(category="restaurant", website_url="https://example.com")
    insp = _inspection(
        reachable=True,
        branded_domain=True,
        has_contact_page=True,
        has_booking_flow=False,
    )
    findings = detect_findings(lead, insp, None)
    angles = [f.angle for f in findings]
    assert "missing_booking" in angles


def test_draft_includes_secondary_finding() -> None:
    lead = _lead(website_url="https://example.com")
    insp = _inspection(
        reachable=False,
        branded_domain=False,
        has_contact_page=False,
    )
    draft = render_draft(lead, insp, None)
    assert draft.primary_angle == "unreachable"
    assert len(draft.findings_used) >= 1
