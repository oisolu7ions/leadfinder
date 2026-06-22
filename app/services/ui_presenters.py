"""Presentation helpers for dashboard templates — no business logic in Jinja."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.business_lead import BusinessLead
from app.models.lead_score import LeadScore
from app.models.website_inspection import WebsiteInspection
from app.services.scoring_rules import PRIORITY_HIGH_MIN, PRIORITY_MEDIUM_MIN, priority_label


@dataclass(frozen=True)
class Badge:
    label: str
    css_class: str


def scan_status_badge(status: str) -> Badge:
    normalized = (status or "unknown").lower()
    labels = {
        "pending": "Pending",
        "running": "Running",
        "completed": "Completed",
        "failed": "Failed",
        "cancelled": "Cancelled",
    }
    return Badge(label=labels.get(normalized, status), css_class=f"badge-scan-{normalized}")


def priority_tier_badge(score: LeadScore | None) -> Badge | None:
    if score is None:
        return None
    tier = None
    if score.breakdown and score.breakdown.get("priority_tier"):
        tier = score.breakdown["priority_tier"]
    elif score.total_score >= PRIORITY_HIGH_MIN:
        tier = "high"
    elif score.total_score >= PRIORITY_MEDIUM_MIN:
        tier = "medium"
    else:
        tier = "low"
    return Badge(label=priority_label(score.total_score), css_class=f"badge-priority-{tier}")


def website_status_badge(
    lead: BusinessLead,
    inspection: WebsiteInspection | None = None,
) -> Badge:
    if not lead.website_url:
        return Badge("No Website", "badge-website-none")
    if inspection and inspection.social_only:
        return Badge("Social Only", "badge-website-social")
    if inspection and inspection.reachable is False:
        return Badge("Unreachable", "badge-website-unreachable")
    if inspection and inspection.branded_domain is True:
        return Badge("Branded Domain", "badge-website-branded")
    if inspection and inspection.branded_domain is False:
        return Badge("Weak Domain", "badge-website-weak")
    if inspection is None:
        return Badge("Unknown", "badge-website-unknown")
    return Badge("Has Website", "badge-website-ok")


def inspection_status_badge(
    lead: BusinessLead,
    inspection: WebsiteInspection | None = None,
) -> Badge:
    if inspection is None or inspection.inspected_at is None:
        return Badge("Uninspected", "badge-insp-uninspected")
    if inspection.error_message:
        return Badge("Error", "badge-insp-error")
    return Badge("Inspected", "badge-insp-done")


def bool_indicator(value: bool | None, *, yes: str = "Yes", no: str = "No", unknown: str = "—") -> str:
    if value is True:
        return yes
    if value is False:
        return no
    return unknown


def bool_badge(value: bool | None, *, yes: str = "Yes", no: str = "No") -> Badge:
    if value is True:
        return Badge(yes, "badge-yes")
    if value is False:
        return Badge(no, "badge-no")
    return Badge("—", "badge-muted")


def outreach_status_badge(status: str | None) -> Badge:
    normalized = (status or "unknown").lower()
    labels = {
        "draft_ready": "Draft Ready",
        "draft": "Draft Ready",
        "reviewed": "Reviewed",
        "approved": "Reviewed",
        "archived": "Archived",
        "rejected": "Archived",
        "sent": "Archived",
    }
    css = {
        "draft_ready": "badge-outreach-ready",
        "draft": "badge-outreach-ready",
        "reviewed": "badge-outreach-reviewed",
        "approved": "badge-outreach-reviewed",
        "archived": "badge-outreach-archived",
    }
    return Badge(
        labels.get(normalized, status or "Unknown"),
        css.get(normalized, "badge-muted"),
    )
