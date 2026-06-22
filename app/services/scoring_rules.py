"""Configurable rule-based scoring weights and priority tiers.

Tune scores here — all scoring logic reads from this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --- Weight matrix (points per signal) ---------------------------------------

WEIGHT_NO_WEBSITE = 35
WEIGHT_SOCIAL_ONLY = 30
WEIGHT_WEAK_BRANDING_FREE_SUBDOMAIN = 15
WEIGHT_WEAK_BRANDING_NON_BRANDED = 10
WEIGHT_UNREACHABLE = 15
WEIGHT_NO_SSL = 8
WEIGHT_POOR_MOBILE = 12
WEIGHT_NO_CONTACT_PAGE = 12
WEIGHT_NO_BOOKING_FLOW = 10
WEIGHT_WEAK_SITE_OUTDATED = 8

# --- Priority tiers (derived from total_score) ---------------------------------

PRIORITY_HIGH_MIN = 50
PRIORITY_MEDIUM_MIN = 25

PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

PRIORITY_LABELS = {
    PRIORITY_HIGH: "High Priority",
    PRIORITY_MEDIUM: "Medium Priority",
    PRIORITY_LOW: "Low Priority",
}

# Categories where missing booking/scheduling is more significant.
BOOKING_SENSITIVE_CATEGORIES = frozenset(
    {
        "restaurant",
        "cafe",
        "salon",
        "barber",
        "dental",
        "dentist",
        "clinic",
        "spa",
        "gym",
        "fitness",
        "hotel",
        "medical",
        "veterinary",
        "vet",
    }
)


@dataclass
class ScoreFactor:
    """One contributing scoring signal."""

    signal: str
    points: int
    detail: str


@dataclass
class ScoreBreakdown:
    """Computed score components ready for persistence."""

    no_website_score: int = 0
    social_only_score: int = 0
    branding_score: int = 0
    reachability_score: int = 0
    ssl_score: int = 0
    mobile_score: int = 0
    contact_flow_score: int = 0
    outdated_website_score: int = 0
    total_score: int = 0
    factors: list[ScoreFactor] = field(default_factory=list)
    scoring_limited: bool = False
    scoring_limited_reason: str | None = None

    def add(self, signal: str, points: int, detail: str, field_name: str) -> None:
        """Record a factor and increment the named sub-score field."""
        if points <= 0:
            return
        self.factors.append(ScoreFactor(signal=signal, points=points, detail=detail))
        current = getattr(self, field_name)
        setattr(self, field_name, current + points)
        self.total_score += points


def is_booking_sensitive_category(category: str | None) -> bool:
    if not category:
        return False
    cat = category.lower()
    return any(keyword in cat for keyword in BOOKING_SENSITIVE_CATEGORIES)


def priority_tier(total_score: int) -> str:
    """Map total score to high / medium / low priority."""
    if total_score >= PRIORITY_HIGH_MIN:
        return PRIORITY_HIGH
    if total_score >= PRIORITY_MEDIUM_MIN:
        return PRIORITY_MEDIUM
    return PRIORITY_LOW


def priority_label(total_score: int) -> str:
    return PRIORITY_LABELS[priority_tier(total_score)]
