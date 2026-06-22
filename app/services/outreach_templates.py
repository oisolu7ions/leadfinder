"""Template-based outreach draft generation — selection and rendering."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.business_lead import BusinessLead
from app.models.lead_score import LeadScore
from app.models.website_inspection import WebsiteInspection
from app.services.scoring_rules import BOOKING_SENSITIVE_CATEGORIES

# Lower number = higher priority when sorting angles.
ANGLE_PRIORITY: dict[str, int] = {
    "no_website": 1,
    "social_only": 2,
    "unreachable": 3,
    "weak_branding": 4,
    "missing_contact": 5,
    "missing_booking": 6,
    "weak_mobile": 7,
    "weak_general": 8,
}

ANGLE_LABELS: dict[str, str] = {
    "no_website": "No dedicated website",
    "social_only": "Social-only web presence",
    "unreachable": "Website unreachable",
    "weak_branding": "Weak or non-branded domain",
    "missing_contact": "Hard-to-find contact path",
    "missing_booking": "No online booking/scheduling flow",
    "weak_mobile": "Poor mobile experience",
    "weak_general": "Room to improve online presence",
}


@dataclass
class DetectedFinding:
    angle: str
    detail: str


@dataclass
class DraftContent:
    subject_line: str
    email_body: str
    short_dm: str
    call_notes: str
    primary_angle: str
    secondary_angles: list[str] = field(default_factory=list)
    findings_used: list[str] = field(default_factory=list)
    tone: str = "professional"


def _is_booking_sensitive(category: str | None) -> bool:
    if not category:
        return False
    return category.strip().lower() in BOOKING_SENSITIVE_CATEGORIES


def detect_findings(
    lead: BusinessLead,
    inspection: WebsiteInspection | None,
    score: LeadScore | None,
) -> list[DetectedFinding]:
    """Detect outreach-relevant findings from stored lead data."""
    findings: list[DetectedFinding] = []

    no_website = not lead.website_url or (inspection and inspection.blank_website)
    if no_website:
        findings.append(
            DetectedFinding(
                angle="no_website",
                detail="No dedicated business website was found.",
            )
        )

    if inspection and inspection.social_only:
        findings.append(
            DetectedFinding(
                angle="social_only",
                detail="Web presence appears limited to social platforms.",
            )
        )

    if inspection and inspection.reachable is False:
        findings.append(
            DetectedFinding(
                angle="unreachable",
                detail="The listed website did not appear reachable during inspection.",
            )
        )

    if inspection and inspection.branded_domain is False and lead.website_url:
        findings.append(
            DetectedFinding(
                angle="weak_branding",
                detail="The site uses a free subdomain or weak branding setup.",
            )
        )

    if inspection and inspection.has_contact_page is False and lead.website_url:
        findings.append(
            DetectedFinding(
                angle="missing_contact",
                detail="A clear contact page or call-to-action was not detected.",
            )
        )

    if (
        inspection
        and inspection.has_booking_flow is False
        and _is_booking_sensitive(lead.category)
        and lead.website_url
        and not no_website
    ):
        findings.append(
            DetectedFinding(
                angle="missing_booking",
                detail=f"No booking/scheduling flow detected for a {lead.category} business.",
            )
        )

    if inspection and inspection.mobile_friendly_basic is False and lead.website_url:
        findings.append(
            DetectedFinding(
                angle="weak_mobile",
                detail="Basic mobile-friendliness checks did not pass.",
            )
        )

    if not findings:
        if score and score.total_score >= 25:
            findings.append(
                DetectedFinding(
                    angle="weak_general",
                    detail="Scoring suggests room to improve web presence and lead capture.",
                )
            )
        else:
            findings.append(
                DetectedFinding(
                    angle="weak_general",
                    detail="There may be room to improve how customers find and contact the business online.",
                )
            )

    findings.sort(key=lambda f: ANGLE_PRIORITY.get(f.angle, 99))
    return findings


def _variant_index(lead_id: int, pool_size: int) -> int:
    return lead_id % pool_size if pool_size else 0


def _observation_sentence(primary: DetectedFinding, secondary: DetectedFinding | None) -> str:
    parts = [primary.detail.rstrip(".")]
    if secondary and secondary.angle != primary.angle:
        parts.append(secondary.detail.rstrip("."))
    return ". ".join(parts) + "."


def _benefit_for_angle(angle: str) -> str:
    benefits = {
        "no_website": (
            "A simple website helps customers verify you're legitimate, find hours and contact info, "
            "and choose you with more confidence."
        ),
        "social_only": (
            "A dedicated website gives you a stable home base online — easier to find in search, "
            "more professional than relying only on social feeds."
        ),
        "unreachable": (
            "When your site works reliably, customers can actually reach you instead of bouncing to a competitor."
        ),
        "weak_branding": (
            "A branded domain and clean site layout build trust and make your business easier to remember."
        ),
        "missing_contact": (
            "Making contact and booking obvious reduces missed calls and walk-away visitors."
        ),
        "missing_booking": (
            "A clear booking or scheduling path helps capture appointments without phone tag."
        ),
        "weak_mobile": (
            "Most local searches happen on phones — a mobile-friendly site keeps those visitors engaged."
        ),
        "weak_general": (
            "Small improvements to clarity, mobile experience, and contact paths often translate to more inquiries."
        ),
    }
    return benefits.get(angle, benefits["weak_general"])


def render_draft(
    lead: BusinessLead,
    inspection: WebsiteInspection | None,
    score: LeadScore | None,
    *,
    tone: str = "professional",
) -> DraftContent:
    """Render outreach content from detected findings."""
    detected = detect_findings(lead, inspection, score)
    primary = detected[0]
    secondary = detected[1] if len(detected) > 1 else None
    business = lead.business_name
    city = lead.city or "your area"
    observation = _observation_sentence(primary, secondary)
    benefit = _benefit_for_angle(primary.angle)

    subjects: dict[str, list[str]] = {
        "no_website": [
            f"Quick question about {business}'s online presence",
            f"A simple website idea for {business}",
            f"Noticed an opportunity for {business} online",
        ],
        "social_only": [
            f"Beyond social — a website idea for {business}",
            f"Quick thought on {business}'s online presence",
        ],
        "unreachable": [
            f"Website accessibility question for {business}",
            f"Quick fix idea for {business}'s site",
        ],
        "weak_branding": [
            f"A stronger web presence idea for {business}",
            f"Quick branding note for {business}",
        ],
        "missing_contact": [
            f"Making it easier for {business} customers to reach you",
            f"A contact-flow idea for {business}",
        ],
        "missing_booking": [
            f"Simpler booking flow idea for {business}",
            f"Quick scheduling improvement for {business}",
        ],
        "weak_mobile": [
            f"Mobile-friendly website idea for {business}",
            f"Quick mobile note for {business}",
        ],
        "weak_general": [
            f"Quick idea for {business}'s online presence",
            f"A practical web improvement for {business}",
        ],
    }

    subject_pool = subjects.get(primary.angle, subjects["weak_general"])
    subject = subject_pool[_variant_index(lead.id, len(subject_pool))]

    email_body = (
        f"Hi,\n\n"
        f"I came across {business} in {city}. {observation}\n\n"
        f"{benefit}\n\n"
        f"We help local businesses with practical, mobile-friendly websites — not pushy sales pitches, "
        f"just a clear path for customers to learn about you and get in touch.\n\n"
        f"Would you be open to a brief 10–15 minute call to share a few specific ideas?\n\n"
        f"Best regards,\n"
        f"OIS Team"
    )

    short_dm = (
        f"Hi — I found {business} in {city}. {primary.detail} "
        f"Happy to share a few practical website ideas if useful. Open to a quick chat?"
    )

    score_note = f"Priority score: {score.total_score}." if score else "Not scored yet."
    call_points = [f"- {f.detail}" for f in detected[:3]]
    call_notes = (
        f"Lead: {business}, {city}\n"
        f"Primary angle: {ANGLE_LABELS.get(primary.angle, primary.angle)}\n"
        f"{score_note}\n\n"
        f"Talking points:\n"
        + "\n".join(call_points)
        + f"\n\nOffer: free 15-min review of their current online presence — review only, no obligation."
    )

    return DraftContent(
        subject_line=subject,
        email_body=email_body,
        short_dm=short_dm,
        call_notes=call_notes,
        primary_angle=primary.angle,
        secondary_angles=[f.angle for f in detected[1:3]],
        findings_used=[f.detail for f in detected[:3]],
        tone=tone,
    )
