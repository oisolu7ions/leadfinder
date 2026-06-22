"""Flatten leads into CSV row dictionaries."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.business_lead import BusinessLead
from app.models.lead_score import LeadScore
from app.models.outreach_draft import OutreachDraft
from app.models.website_inspection import WebsiteInspection
from app.services.lead import latest_inspection, latest_score
from app.services.scoring_rules import PRIORITY_HIGH_MIN, PRIORITY_MEDIUM_MIN, priority_label

EXPORT_CSV_COLUMNS: list[str] = [
    # Lead basics
    "lead_id",
    "business_name",
    "category",
    "phone",
    "email",
    "address_line1",
    "city",
    "state",
    "postal_code",
    "country",
    "website_url",
    "normalized_domain",
    "source_name",
    "source_url",
    "lead_status",
    "updated_at",
    # Inspection summary
    "inspection_status",
    "inspected_at",
    "final_url",
    "reachable",
    "blank_website",
    "social_only",
    "branded_domain",
    "mobile_friendly_basic",
    "has_contact_page",
    "has_booking_flow",
    "ssl_present",
    "http_status",
    # Score summary
    "total_score",
    "priority_tier",
    "no_website_score",
    "outdated_website_score",
    "mobile_score",
    "branding_score",
    "contact_flow_score",
    "social_only_score",
    # Outreach summary
    "outreach_status",
    "latest_draft_created_at",
    "latest_draft_subject_line",
]


def _fmt_dt(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _fmt_bool(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return ""


def _priority_tier(score: LeadScore | None) -> str:
    if score is None:
        return ""
    if score.breakdown and score.breakdown.get("priority_tier"):
        return str(score.breakdown["priority_tier"])
    if score.total_score >= PRIORITY_HIGH_MIN:
        return "high"
    if score.total_score >= PRIORITY_MEDIUM_MIN:
        return "medium"
    return "low"


def _inspection_status(inspection: WebsiteInspection | None) -> str:
    if inspection is None or inspection.inspected_at is None:
        return "uninspected"
    if inspection.error_message:
        return "error"
    return "inspected"


def lead_to_export_row(lead: BusinessLead) -> dict[str, Any]:
    """Build a flat export row for one lead."""
    inspection = latest_inspection(lead)
    score = latest_score(lead)
    draft: OutreachDraft | None = lead.outreach_drafts[0] if lead.outreach_drafts else None

    return {
        "lead_id": lead.id,
        "business_name": lead.business_name,
        "category": lead.category or "",
        "phone": lead.phone or "",
        "email": lead.email or "",
        "address_line1": lead.address_line1 or "",
        "city": lead.city or "",
        "state": lead.state or "",
        "postal_code": lead.postal_code or "",
        "country": lead.country or "",
        "website_url": lead.website_url or "",
        "normalized_domain": lead.normalized_domain or "",
        "source_name": lead.source_name,
        "source_url": lead.source_url or "",
        "lead_status": lead.status,
        "updated_at": _fmt_dt(lead.updated_at),
        "inspection_status": _inspection_status(inspection),
        "inspected_at": _fmt_dt(inspection.inspected_at if inspection else None),
        "final_url": (inspection.final_url if inspection else None) or "",
        "reachable": _fmt_bool(inspection.reachable if inspection else None),
        "blank_website": _fmt_bool(inspection.blank_website if inspection else None),
        "social_only": _fmt_bool(inspection.social_only if inspection else None),
        "branded_domain": _fmt_bool(inspection.branded_domain if inspection else None),
        "mobile_friendly_basic": _fmt_bool(inspection.mobile_friendly_basic if inspection else None),
        "has_contact_page": _fmt_bool(inspection.has_contact_page if inspection else None),
        "has_booking_flow": _fmt_bool(inspection.has_booking_flow if inspection else None),
        "ssl_present": _fmt_bool(inspection.ssl_present if inspection else None),
        "http_status": str(inspection.http_status) if inspection and inspection.http_status else "",
        "total_score": score.total_score if score else "",
        "priority_tier": _priority_tier(score),
        "no_website_score": score.no_website_score if score else "",
        "outdated_website_score": score.outdated_website_score if score else "",
        "mobile_score": score.mobile_score if score else "",
        "branding_score": score.branding_score if score else "",
        "contact_flow_score": score.contact_flow_score if score else "",
        "social_only_score": score.social_only_score if score else "",
        "outreach_status": draft.status if draft else "",
        "latest_draft_created_at": _fmt_dt(draft.created_at if draft else None),
        "latest_draft_subject_line": draft.subject_line if draft else "",
    }


def row_to_csv_values(row: dict[str, Any]) -> list[Any]:
    return [row.get(col, "") for col in EXPORT_CSV_COLUMNS]
