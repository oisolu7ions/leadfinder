"""Dashboard metrics and operational queues."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.business_lead import BusinessLead
from app.models.enums import ACTIVE_DRAFT_STATUSES, REVIEWED_DRAFT_STATUSES, OutreachDraftStatus, ScanJobStatus
from app.models.lead_score import LeadScore
from app.models.outreach_draft import OutreachDraft
from app.models.scan_job import ScanJob
from app.models.website_inspection import WebsiteInspection
from app.services.lead import LeadFilters, count_uninspected_leads, list_leads
from app.services.scoring_rules import PRIORITY_HIGH_MIN, PRIORITY_MEDIUM_MIN
from app.services.scan import list_scan_jobs


@dataclass
class KpiMetrics:
    total_leads: int
    uninspected: int
    high_priority: int
    no_website: int
    social_only: int
    recent_scans: int
    drafts_ready: int


@dataclass
class InspectionSummary:
    total: int
    reachable: int
    unreachable: int
    social_only: int
    with_errors: int


@dataclass
class ScoreSummary:
    high: int
    medium: int
    low: int
    unscored: int


@dataclass
class OutreachSummary:
    total_drafts: int
    ready: int
    approved: int


@dataclass
class NamedCount:
    name: str
    count: int


def _latest_score_subquery():
    return (
        select(
            LeadScore.business_lead_id.label("lead_id"),
            func.max(LeadScore.scored_at).label("max_scored_at"),
        )
        .group_by(LeadScore.business_lead_id)
        .subquery()
    )


def _latest_inspection_subquery():
    return (
        select(
            WebsiteInspection.business_lead_id.label("lead_id"),
            func.max(WebsiteInspection.inspected_at).label("max_inspected_at"),
        )
        .group_by(WebsiteInspection.business_lead_id)
        .subquery()
    )


def get_kpi_metrics(db: Session) -> KpiMetrics:
    total_leads = db.scalar(select(func.count()).select_from(BusinessLead)) or 0
    uninspected = count_uninspected_leads(db)
    latest_score = _latest_score_subquery()
    high_priority = (
        db.scalar(
            select(func.count())
            .select_from(BusinessLead)
            .join(latest_score, latest_score.c.lead_id == BusinessLead.id)
            .join(
                LeadScore,
                (LeadScore.business_lead_id == BusinessLead.id)
                & (LeadScore.scored_at == latest_score.c.max_scored_at),
            )
            .where(LeadScore.total_score >= PRIORITY_HIGH_MIN)
        )
        or 0
    )
    no_website = (
        db.scalar(
            select(func.count())
            .select_from(BusinessLead)
            .where(or_(BusinessLead.website_url.is_(None), BusinessLead.website_url == ""))
        )
        or 0
    )
    social_only = (
        db.scalar(
            select(func.count())
            .select_from(WebsiteInspection)
            .where(WebsiteInspection.social_only.is_(True))
        )
        or 0
    )
    recent_scans = (
        db.scalar(
            select(func.count())
            .select_from(ScanJob)
            .where(ScanJob.status == ScanJobStatus.COMPLETED.value)
        )
        or 0
    )
    drafts_ready = (
        db.scalar(
            select(func.count())
            .select_from(OutreachDraft)
            .where(OutreachDraft.status.in_(ACTIVE_DRAFT_STATUSES))
        )
        or 0
    )
    return KpiMetrics(
        total_leads=total_leads,
        uninspected=uninspected,
        high_priority=high_priority,
        no_website=no_website,
        social_only=social_only,
        recent_scans=recent_scans,
        drafts_ready=drafts_ready,
    )


def list_needs_review_leads(db: Session, limit: int = 10) -> list[BusinessLead]:
    """Leads needing attention: uninspected, unscored, or high priority."""
    latest_score = _latest_score_subquery()
    latest_insp = _latest_inspection_subquery()
    stmt = (
        select(BusinessLead)
        .outerjoin(latest_insp, latest_insp.c.lead_id == BusinessLead.id)
        .outerjoin(latest_score, latest_score.c.lead_id == BusinessLead.id)
        .outerjoin(
            LeadScore,
            (LeadScore.business_lead_id == BusinessLead.id)
            & (LeadScore.scored_at == latest_score.c.max_scored_at),
        )
        .where(
            or_(
                latest_insp.c.max_inspected_at.is_(None),
                LeadScore.id.is_(None),
                LeadScore.total_score >= PRIORITY_HIGH_MIN,
            )
        )
        .order_by(LeadScore.total_score.desc().nulls_last(), BusinessLead.updated_at.desc())
        .limit(limit)
        .options(
            selectinload(BusinessLead.scores),
            selectinload(BusinessLead.inspections),
        )
    )
    return list(db.scalars(stmt).unique().all())


def get_inspection_summary(db: Session) -> InspectionSummary:
    total = db.scalar(select(func.count()).select_from(WebsiteInspection)) or 0
    reachable = (
        db.scalar(
            select(func.count())
            .select_from(WebsiteInspection)
            .where(WebsiteInspection.reachable.is_(True))
        )
        or 0
    )
    unreachable = (
        db.scalar(
            select(func.count())
            .select_from(WebsiteInspection)
            .where(WebsiteInspection.reachable.is_(False))
        )
        or 0
    )
    social_only = (
        db.scalar(
            select(func.count())
            .select_from(WebsiteInspection)
            .where(WebsiteInspection.social_only.is_(True))
        )
        or 0
    )
    with_errors = (
        db.scalar(
            select(func.count())
            .select_from(WebsiteInspection)
            .where(WebsiteInspection.error_message.isnot(None))
        )
        or 0
    )
    return InspectionSummary(
        total=total,
        reachable=reachable,
        unreachable=unreachable,
        social_only=social_only,
        with_errors=with_errors,
    )


def get_score_summary(db: Session) -> ScoreSummary:
    latest_score = _latest_score_subquery()
    scored_leads = (
        select(BusinessLead.id)
        .join(latest_score, latest_score.c.lead_id == BusinessLead.id)
        .join(
            LeadScore,
            (LeadScore.business_lead_id == BusinessLead.id)
            & (LeadScore.scored_at == latest_score.c.max_scored_at),
        )
        .subquery()
    )
    high = (
        db.scalar(
            select(func.count())
            .select_from(scored_leads)
            .join(BusinessLead, BusinessLead.id == scored_leads.c.id)
            .join(latest_score, latest_score.c.lead_id == BusinessLead.id)
            .join(
                LeadScore,
                (LeadScore.business_lead_id == BusinessLead.id)
                & (LeadScore.scored_at == latest_score.c.max_scored_at),
            )
            .where(LeadScore.total_score >= PRIORITY_HIGH_MIN)
        )
        or 0
    )
    medium = (
        db.scalar(
            select(func.count())
            .select_from(scored_leads)
            .join(BusinessLead, BusinessLead.id == scored_leads.c.id)
            .join(latest_score, latest_score.c.lead_id == BusinessLead.id)
            .join(
                LeadScore,
                (LeadScore.business_lead_id == BusinessLead.id)
                & (LeadScore.scored_at == latest_score.c.max_scored_at),
            )
            .where(
                LeadScore.total_score >= PRIORITY_MEDIUM_MIN,
                LeadScore.total_score < PRIORITY_HIGH_MIN,
            )
        )
        or 0
    )
    low = (
        db.scalar(
            select(func.count())
            .select_from(scored_leads)
            .join(BusinessLead, BusinessLead.id == scored_leads.c.id)
            .join(latest_score, latest_score.c.lead_id == BusinessLead.id)
            .join(
                LeadScore,
                (LeadScore.business_lead_id == BusinessLead.id)
                & (LeadScore.scored_at == latest_score.c.max_scored_at),
            )
            .where(LeadScore.total_score < PRIORITY_MEDIUM_MIN)
        )
        or 0
    )
    total_leads = db.scalar(select(func.count()).select_from(BusinessLead)) or 0
    scored_count = db.scalar(select(func.count()).select_from(scored_leads)) or 0
    return ScoreSummary(
        high=high,
        medium=medium,
        low=low,
        unscored=max(0, total_leads - scored_count),
    )


def get_outreach_summary(db: Session) -> OutreachSummary:
    total = db.scalar(select(func.count()).select_from(OutreachDraft)) or 0
    ready = (
        db.scalar(
            select(func.count())
            .select_from(OutreachDraft)
            .where(OutreachDraft.status.in_(ACTIVE_DRAFT_STATUSES))
        )
        or 0
    )
    reviewed = (
        db.scalar(
            select(func.count())
            .select_from(OutreachDraft)
            .where(OutreachDraft.status.in_(REVIEWED_DRAFT_STATUSES))
        )
        or 0
    )
    return OutreachSummary(total_drafts=total, ready=ready, approved=reviewed)


def get_top_categories(db: Session, limit: int = 5) -> list[NamedCount]:
    rows = db.execute(
        select(BusinessLead.category, func.count())
        .where(BusinessLead.category.isnot(None), BusinessLead.category != "")
        .group_by(BusinessLead.category)
        .order_by(func.count().desc())
        .limit(limit)
    ).all()
    return [NamedCount(name=row[0], count=row[1]) for row in rows]


def get_top_cities(db: Session, limit: int = 5) -> list[NamedCount]:
    rows = db.execute(
        select(BusinessLead.city, func.count())
        .where(BusinessLead.city.isnot(None), BusinessLead.city != "")
        .group_by(BusinessLead.city)
        .order_by(func.count().desc())
        .limit(limit)
    ).all()
    return [NamedCount(name=row[0], count=row[1]) for row in rows]


def get_dashboard_data(db: Session) -> dict:
    """Aggregate all dashboard view data."""
    return {
        "kpis": get_kpi_metrics(db),
        "needs_review": list_needs_review_leads(db, limit=10),
        "recent_leads": list_leads(db, LeadFilters(page=1, per_page=8, sort_by="updated")).leads,
        "recent_scans": list_scan_jobs(db, limit=8),
        "inspection_summary": get_inspection_summary(db),
        "score_summary": get_score_summary(db),
        "top_categories": get_top_categories(db),
        "top_cities": get_top_cities(db),
        "outreach_summary": get_outreach_summary(db),
    }
