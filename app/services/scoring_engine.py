"""Apply scoring rules to lead + inspection data."""

from __future__ import annotations

from app.models.business_lead import BusinessLead
from app.models.website_inspection import WebsiteInspection
from app.services.scoring_rules import (
    WEIGHT_NO_BOOKING_FLOW,
    WEIGHT_NO_CONTACT_PAGE,
    WEIGHT_NO_SSL,
    WEIGHT_NO_WEBSITE,
    WEIGHT_POOR_MOBILE,
    WEIGHT_SOCIAL_ONLY,
    WEIGHT_UNREACHABLE,
    WEIGHT_WEAK_BRANDING_FREE_SUBDOMAIN,
    WEIGHT_WEAK_BRANDING_NON_BRANDED,
    WEIGHT_WEAK_SITE_OUTDATED,
    ScoreBreakdown,
    ScoreFactor,
    is_booking_sensitive_category,
)
from app.utils.normalize import extract_domain, is_free_subdomain, is_social_host


def compute_score_breakdown(
    lead: BusinessLead,
    inspection: WebsiteInspection | None,
) -> ScoreBreakdown:
    """Evaluate all scoring rules and return an explainable breakdown."""
    breakdown = ScoreBreakdown()
    domain = extract_domain(lead.website_url)

    # --- No website ------------------------------------------------------------
    if not lead.website_url:
        breakdown.add(
            "no_website",
            WEIGHT_NO_WEBSITE,
            "No website URL on record",
            "no_website_score",
        )
    elif inspection and inspection.blank_website:
        breakdown.add(
            "no_website",
            WEIGHT_NO_WEBSITE,
            "Website field is blank",
            "no_website_score",
        )

    # --- Social-only presence --------------------------------------------------
    if inspection and inspection.social_only:
        breakdown.add(
            "social_only",
            WEIGHT_SOCIAL_ONLY,
            "Web presence is social/directory only",
            "social_only_score",
        )
    elif domain and is_social_host(domain):
        breakdown.add(
            "social_only",
            WEIGHT_SOCIAL_ONLY,
            f"Website URL points to social host ({domain})",
            "social_only_score",
        )

    # --- Branding / domain quality ---------------------------------------------
    if domain and is_free_subdomain(domain):
        breakdown.add(
            "weak_branding",
            WEIGHT_WEAK_BRANDING_FREE_SUBDOMAIN,
            f"Free-hosted subdomain ({domain})",
            "branding_score",
        )
    elif inspection and inspection.branded_domain is False and not breakdown.social_only_score:
        breakdown.add(
            "weak_branding",
            WEIGHT_WEAK_BRANDING_NON_BRANDED,
            "Non-branded domain pattern",
            "branding_score",
        )

    if inspection is None and lead.website_url and not breakdown.no_website_score:
        breakdown.scoring_limited = True
        breakdown.scoring_limited_reason = (
            "No inspection data — reachability, mobile, contact, and SSL rules skipped"
        )
        if not breakdown.factors:
            breakdown.factors.append(
            ScoreFactor(
                signal="limited",
                points=0,
                detail=breakdown.scoring_limited_reason,
            )
        )
        return breakdown

    if inspection is None:
        return breakdown

    # --- Reachability ----------------------------------------------------------
    if inspection.reachable is False:
        breakdown.add(
            "unreachable",
            WEIGHT_UNREACHABLE,
            "Website unreachable or HTTP error",
            "reachability_score",
        )

    # --- SSL -------------------------------------------------------------------
    if inspection.ssl_present is False and not breakdown.no_website_score:
        breakdown.add(
            "no_ssl",
            WEIGHT_NO_SSL,
            "Site not served over HTTPS",
            "ssl_score",
        )

    # --- Mobile ----------------------------------------------------------------
    if inspection.mobile_friendly_basic is False and inspection.reachable is not False:
        breakdown.add(
            "poor_mobile",
            WEIGHT_POOR_MOBILE,
            "Basic mobile-friendliness check failed",
            "mobile_score",
        )

    # --- Contact page ----------------------------------------------------------
    if inspection.has_contact_page is False and inspection.reachable is not False:
        breakdown.add(
            "no_contact_page",
            WEIGHT_NO_CONTACT_PAGE,
            "No obvious contact page or contact CTA",
            "contact_flow_score",
        )

    # --- Booking flow (category-sensitive) ---------------------------------------
    if (
        inspection.has_booking_flow is False
        and inspection.reachable is not False
        and is_booking_sensitive_category(lead.category)
    ):
        breakdown.add(
            "no_booking_flow",
            WEIGHT_NO_BOOKING_FLOW,
            f"No booking/scheduling flow for category '{lead.category}'",
            "contact_flow_score",
        )

    # --- Weak / outdated site heuristic ----------------------------------------
    if (
        inspection.reachable is True
        and not inspection.page_title
        and not breakdown.no_website_score
        and not breakdown.social_only_score
    ):
        breakdown.add(
            "weak_site",
            WEIGHT_WEAK_SITE_OUTDATED,
            "Reachable site missing page title (weak/outdated signal)",
            "outdated_website_score",
        )

    if not breakdown.factors and not breakdown.scoring_limited:
        breakdown.factors.append(
            ScoreFactor(
                signal="decent_presence",
                points=0,
                detail="No significant web-presence weaknesses detected",
            )
        )

    return breakdown


def breakdown_to_notes(breakdown: ScoreBreakdown) -> str:
    """Human-readable multi-line explanation."""
    lines = [f"+{f.points} {f.detail}" for f in breakdown.factors if f.points > 0]
    if breakdown.scoring_limited_reason:
        lines.append(f"Note: {breakdown.scoring_limited_reason}")
    if not lines:
        return "No significant opportunity signals."
    return "\n".join(lines)


def breakdown_to_json(breakdown: ScoreBreakdown) -> dict:
    """Structured breakdown for API/dashboard."""
    from app.services.scoring_rules import priority_label, priority_tier

    return {
        "total_score": breakdown.total_score,
        "priority_tier": priority_tier(breakdown.total_score),
        "priority_label": priority_label(breakdown.total_score),
        "scoring_limited": breakdown.scoring_limited,
        "scoring_limited_reason": breakdown.scoring_limited_reason,
        "factors": [
            {"signal": f.signal, "points": f.points, "detail": f.detail}
            for f in breakdown.factors
        ],
        "sub_scores": {
            "no_website_score": breakdown.no_website_score,
            "social_only_score": breakdown.social_only_score,
            "branding_score": breakdown.branding_score,
            "reachability_score": breakdown.reachability_score,
            "ssl_score": breakdown.ssl_score,
            "mobile_score": breakdown.mobile_score,
            "contact_flow_score": breakdown.contact_flow_score,
            "outdated_website_score": breakdown.outdated_website_score,
        },
    }
