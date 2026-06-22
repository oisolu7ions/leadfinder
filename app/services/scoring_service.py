"""Lead scoring orchestration and persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.logging import get_logger
from app.models.business_lead import BusinessLead
from app.models.lead_score import LeadScore
from app.models.website_inspection import WebsiteInspection
from app.services.audit import log_action
from app.services.lead import latest_inspection, latest_score
from app.services.scoring_engine import (
    breakdown_to_json,
    breakdown_to_notes,
    compute_score_breakdown,
)
from app.services.scoring_rules import priority_label, priority_tier

logger = get_logger(__name__)


def _load_lead(db: Session, lead_id: int) -> BusinessLead:
    lead = db.scalar(
        select(BusinessLead)
        .where(BusinessLead.id == lead_id)
        .options(
            selectinload(BusinessLead.inspections),
            selectinload(BusinessLead.scores),
        )
    )
    if lead is None:
        raise ValueError(f"Lead {lead_id} not found")
    return lead


def score_lead(
    db: Session,
    lead_id: int,
    inspection: WebsiteInspection | None = None,
    *,
    commit: bool = True,
) -> LeadScore:
    """Compute and persist a new score record for a lead."""
    lead = _load_lead(db, lead_id)
    if inspection is None:
        inspection = latest_inspection(lead)

    breakdown = compute_score_breakdown(lead, inspection)
    breakdown_json = breakdown_to_json(breakdown)

    score = LeadScore(
        business_lead_id=lead.id,
        scored_at=datetime.now(UTC),
        total_score=breakdown.total_score,
        no_website_score=breakdown.no_website_score,
        social_only_score=breakdown.social_only_score,
        branding_score=breakdown.branding_score,
        reachability_score=breakdown.reachability_score,
        ssl_score=breakdown.ssl_score,
        mobile_score=breakdown.mobile_score,
        contact_flow_score=breakdown.contact_flow_score,
        outdated_website_score=breakdown.outdated_website_score,
        notes=breakdown_to_notes(breakdown),
        breakdown=breakdown_json,
    )
    db.add(score)
    db.flush()

    log_action(
        db,
        "lead_scored",
        "business_lead",
        lead.id,
        details={
            "score_id": score.id,
            "total_score": breakdown.total_score,
            "priority_tier": priority_tier(breakdown.total_score),
        },
    )

    if commit:
        db.commit()
        db.refresh(score)

    logger.info(
        "lead_scored",
        lead_id=lead_id,
        total_score=breakdown.total_score,
        priority=priority_tier(breakdown.total_score),
        limited=breakdown.scoring_limited,
    )
    return score


def rescore_lead(db: Session, lead_id: int, *, commit: bool = True) -> LeadScore:
    """Recompute score using the latest inspection data."""
    return score_lead(db, lead_id, commit=commit)


def get_lead_score(db: Session, lead_id: int) -> LeadScore | None:
    lead = db.get(BusinessLead, lead_id)
    if lead is None:
        return None
    return latest_score(lead) if lead.scores else db.scalar(
        select(LeadScore)
        .where(LeadScore.business_lead_id == lead_id)
        .order_by(LeadScore.scored_at.desc())
        .limit(1)
    )


def list_lead_scores(
    db: Session,
    lead_id: int,
    *,
    limit: int = 20,
) -> list[LeadScore]:
    return list(
        db.scalars(
            select(LeadScore)
            .where(LeadScore.business_lead_id == lead_id)
            .order_by(LeadScore.scored_at.desc())
            .limit(limit)
        ).all()
    )


def _latest_score_subquery():
    return (
        select(
            LeadScore.business_lead_id.label("lead_id"),
            func.max(LeadScore.scored_at).label("max_scored_at"),
        )
        .group_by(LeadScore.business_lead_id)
        .subquery()
    )


def list_unscored_lead_ids(db: Session, limit: int = 100) -> list[int]:
    """Return lead IDs that have never been scored."""
    latest = _latest_score_subquery()
    stmt = (
        select(BusinessLead.id)
        .outerjoin(latest, latest.c.lead_id == BusinessLead.id)
        .where(latest.c.max_scored_at.is_(None))
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def score_unscored_leads(db: Session, limit: int = 50) -> dict[str, int]:
    """Score leads that have no score record yet."""
    lead_ids = list_unscored_lead_ids(db, limit=limit)
    scored = errors = 0
    for lead_id in lead_ids:
        try:
            score_lead(db, lead_id, commit=True)
            scored += 1
        except Exception:
            logger.exception("bulk_score_failed", lead_id=lead_id)
            errors += 1
            db.rollback()
    return {"scored": scored, "errors": errors, "attempted": len(lead_ids)}


def rescore_leads_with_inspections(db: Session, limit: int = 50) -> dict[str, int]:
    """Rescore leads that have at least one inspection."""
    latest_insp = (
        select(
            WebsiteInspection.business_lead_id.label("lead_id"),
            func.max(WebsiteInspection.inspected_at).label("max_inspected"),
        )
        .group_by(WebsiteInspection.business_lead_id)
        .subquery()
    )
    stmt = (
        select(BusinessLead.id)
        .join(latest_insp, latest_insp.c.lead_id == BusinessLead.id)
        .where(latest_insp.c.max_inspected.isnot(None))
        .limit(limit)
    )
    lead_ids = list(db.scalars(stmt).all())
    rescored = errors = 0
    for lead_id in lead_ids:
        try:
            rescore_lead(db, lead_id, commit=True)
            rescored += 1
        except Exception:
            logger.exception("bulk_rescore_failed", lead_id=lead_id)
            errors += 1
            db.rollback()
    return {"rescored": rescored, "errors": errors, "attempted": len(lead_ids)}


def get_priority_for_score(score: LeadScore | None) -> str | None:
    if score is None:
        return None
    if score.breakdown and "priority_tier" in score.breakdown:
        return score.breakdown["priority_tier"]
    return priority_tier(score.total_score)


def get_priority_label_for_score(score: LeadScore | None) -> str | None:
    if score is None:
        return None
    if score.breakdown and "priority_label" in score.breakdown:
        return score.breakdown["priority_label"]
    return priority_label(score.total_score)
