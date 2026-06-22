"""Business lead persistence, deduplication, and querying."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.business_lead import BusinessLead
from app.models.lead_score import LeadScore
from app.models.website_inspection import WebsiteInspection
from app.services.lead_persistence import upsert_lead


@dataclass
class LeadFilters:
    """Filter parameters for lead list queries."""

    city: str | None = None
    state: str | None = None
    category: str | None = None
    status: str | None = None
    has_website: str | None = None  # yes | no
    social_only: str | None = None  # yes | no
    min_score: int | None = None
    max_score: int | None = None
    inspected: str | None = None  # yes | no
    outreach_status: str | None = None
    search: str | None = None
    priority: str | None = None  # high | medium | low
    source_name: str | None = None
    insp_reachable: str | None = None  # yes | no
    insp_blank_website: str | None = None
    insp_social_only: str | None = None
    insp_has_contact_page: str | None = None
    insp_has_booking_flow: str | None = None
    sort_by: str = "updated"  # updated | score_desc
    page: int = 1
    per_page: int = 25


@dataclass
class LeadListResult:
    leads: list[BusinessLead]
    total: int
    page: int
    per_page: int


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


def build_leads_query(filters: LeadFilters) -> Select[tuple[BusinessLead]]:
    """Build a filtered lead query."""
    stmt = select(BusinessLead)

    if filters.city:
        stmt = stmt.where(BusinessLead.city.ilike(f"%{filters.city.strip()}%"))
    if filters.state:
        stmt = stmt.where(BusinessLead.state.ilike(f"%{filters.state.strip()}%"))
    if filters.category:
        stmt = stmt.where(BusinessLead.category.ilike(f"%{filters.category.strip()}%"))
    if filters.source_name:
        stmt = stmt.where(BusinessLead.source_name.ilike(f"%{filters.source_name.strip()}%"))
    if filters.status:
        stmt = stmt.where(BusinessLead.status == filters.status)

    if filters.has_website == "yes":
        stmt = stmt.where(BusinessLead.website_url.isnot(None), BusinessLead.website_url != "")
    elif filters.has_website == "no":
        stmt = stmt.where(or_(BusinessLead.website_url.is_(None), BusinessLead.website_url == ""))

    if filters.search:
        term = f"%{filters.search.strip()}%"
        stmt = stmt.where(
            or_(
                BusinessLead.business_name.ilike(term),
                BusinessLead.phone.ilike(term),
                BusinessLead.city.ilike(term),
                BusinessLead.normalized_domain.ilike(term),
            )
        )

    if (
        filters.min_score is not None
        or filters.max_score is not None
        or filters.social_only
        or filters.priority
    ):
        latest_score = _latest_score_subquery()
        stmt = stmt.outerjoin(latest_score, latest_score.c.lead_id == BusinessLead.id)
        stmt = stmt.outerjoin(
            LeadScore,
            (LeadScore.business_lead_id == BusinessLead.id)
            & (LeadScore.scored_at == latest_score.c.max_scored_at),
        )
        if filters.min_score is not None:
            stmt = stmt.where(LeadScore.total_score >= filters.min_score)
        if filters.max_score is not None:
            stmt = stmt.where(LeadScore.total_score <= filters.max_score)
        if filters.social_only == "yes":
            stmt = stmt.where(LeadScore.social_only_score > 0)
        elif filters.social_only == "no":
            stmt = stmt.where(
                or_(LeadScore.social_only_score == 0, LeadScore.social_only_score.is_(None))
            )
        if filters.priority:
            from app.services.scoring_rules import PRIORITY_HIGH_MIN, PRIORITY_MEDIUM_MIN

            if filters.priority == "high":
                stmt = stmt.where(LeadScore.total_score >= PRIORITY_HIGH_MIN)
            elif filters.priority == "medium":
                stmt = stmt.where(
                    LeadScore.total_score >= PRIORITY_MEDIUM_MIN,
                    LeadScore.total_score < PRIORITY_HIGH_MIN,
                )
            elif filters.priority == "low":
                stmt = stmt.where(LeadScore.total_score < PRIORITY_MEDIUM_MIN)

    if filters.inspected or filters.outreach_status:
        if filters.inspected:
            latest_insp = _latest_inspection_subquery()
            stmt = stmt.outerjoin(latest_insp, latest_insp.c.lead_id == BusinessLead.id)
            if filters.inspected == "yes":
                stmt = stmt.where(latest_insp.c.max_inspected_at.isnot(None))
            elif filters.inspected == "no":
                stmt = stmt.where(latest_insp.c.max_inspected_at.is_(None))

    if filters.outreach_status:
        from app.models.outreach_draft import OutreachDraft

        latest_draft = (
            select(
                OutreachDraft.business_lead_id.label("lead_id"),
                func.max(OutreachDraft.created_at).label("max_created_at"),
            )
            .group_by(OutreachDraft.business_lead_id)
            .subquery()
        )
        stmt = stmt.outerjoin(latest_draft, latest_draft.c.lead_id == BusinessLead.id)
        stmt = stmt.outerjoin(
            OutreachDraft,
            (OutreachDraft.business_lead_id == BusinessLead.id)
            & (OutreachDraft.created_at == latest_draft.c.max_created_at),
        )
        stmt = stmt.where(OutreachDraft.status == filters.outreach_status)

    insp_filter_keys = (
        filters.insp_reachable,
        filters.insp_blank_website,
        filters.insp_social_only,
        filters.insp_has_contact_page,
        filters.insp_has_booking_flow,
    )
    if any(insp_filter_keys):
        latest_insp = _latest_inspection_subquery()
        stmt = stmt.join(latest_insp, latest_insp.c.lead_id == BusinessLead.id)
        stmt = stmt.join(
            WebsiteInspection,
            (WebsiteInspection.business_lead_id == BusinessLead.id)
            & (WebsiteInspection.inspected_at == latest_insp.c.max_inspected_at),
        )
        if filters.insp_reachable == "yes":
            stmt = stmt.where(WebsiteInspection.reachable.is_(True))
        elif filters.insp_reachable == "no":
            stmt = stmt.where(WebsiteInspection.reachable.is_(False))
        if filters.insp_blank_website == "yes":
            stmt = stmt.where(WebsiteInspection.blank_website.is_(True))
        elif filters.insp_blank_website == "no":
            stmt = stmt.where(WebsiteInspection.blank_website.is_(False))
        if filters.insp_social_only == "yes":
            stmt = stmt.where(WebsiteInspection.social_only.is_(True))
        elif filters.insp_social_only == "no":
            stmt = stmt.where(WebsiteInspection.social_only.is_(False))
        if filters.insp_has_contact_page == "yes":
            stmt = stmt.where(WebsiteInspection.has_contact_page.is_(True))
        elif filters.insp_has_contact_page == "no":
            stmt = stmt.where(WebsiteInspection.has_contact_page.is_(False))
        if filters.insp_has_booking_flow == "yes":
            stmt = stmt.where(WebsiteInspection.has_booking_flow.is_(True))
        elif filters.insp_has_booking_flow == "no":
            stmt = stmt.where(WebsiteInspection.has_booking_flow.is_(False))

    return stmt


def list_leads(db: Session, filters: LeadFilters) -> LeadListResult:
    """Return paginated filtered leads."""
    base = build_leads_query(filters)
    count_subq = base.with_only_columns(BusinessLead.id).distinct().subquery()
    total = db.scalar(select(func.count()).select_from(count_subq)) or 0
    offset = (filters.page - 1) * filters.per_page

    if filters.sort_by == "score_desc":
        latest_score = _latest_score_subquery()
        base = base.outerjoin(latest_score, latest_score.c.lead_id == BusinessLead.id)
        base = base.outerjoin(
            LeadScore,
            (LeadScore.business_lead_id == BusinessLead.id)
            & (LeadScore.scored_at == latest_score.c.max_scored_at),
        )
        order = (LeadScore.total_score.desc().nulls_last(), BusinessLead.updated_at.desc())
    else:
        order = (BusinessLead.updated_at.desc(),)

    stmt = (
        base.order_by(*order)
        .offset(offset)
        .limit(filters.per_page)
        .options(
            selectinload(BusinessLead.scores),
            selectinload(BusinessLead.inspections),
            selectinload(BusinessLead.outreach_drafts),
        )
    )
    leads = list(db.scalars(stmt).unique().all())
    return LeadListResult(leads=leads, total=total, page=filters.page, per_page=filters.per_page)


def get_lead(db: Session, lead_id: int) -> BusinessLead | None:
    """Load a lead with related inspection, score, and draft data."""
    return db.scalar(
        select(BusinessLead)
        .where(BusinessLead.id == lead_id)
        .options(
            selectinload(BusinessLead.inspections),
            selectinload(BusinessLead.scores),
            selectinload(BusinessLead.outreach_drafts),
            selectinload(BusinessLead.scan_job),
        )
    )


def latest_score(lead: BusinessLead) -> LeadScore | None:
    return lead.scores[0] if lead.scores else None


def latest_inspection(lead: BusinessLead) -> WebsiteInspection | None:
    return lead.inspections[0] if lead.inspections else None


def count_uninspected_leads(db: Session) -> int:
    """Count leads with no completed inspection."""
    latest_insp = _latest_inspection_subquery()
    return (
        db.scalar(
            select(func.count())
            .select_from(BusinessLead)
            .outerjoin(latest_insp, latest_insp.c.lead_id == BusinessLead.id)
            .where(latest_insp.c.max_inspected_at.is_(None))
        )
        or 0
    )


def list_uninspected_lead_ids(db: Session, limit: int = 100) -> list[int]:
    """Return IDs of leads with no completed inspection."""
    latest_insp = _latest_inspection_subquery()
    stmt = (
        select(BusinessLead.id)
        .outerjoin(latest_insp, latest_insp.c.lead_id == BusinessLead.id)
        .where(latest_insp.c.max_inspected_at.is_(None))
        .limit(limit)
    )
    return list(db.scalars(stmt).all())
