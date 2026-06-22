"""Outreach draft generation, retrieval, and status management."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.logging import get_logger
from app.models.business_lead import BusinessLead
from app.models.enums import OutreachDraftStatus
from app.models.outreach_draft import OutreachDraft
from app.services.audit import log_action
from app.services.lead import get_lead, latest_inspection, latest_score
from app.services.outreach_templates import ANGLE_LABELS, DraftContent, render_draft

logger = get_logger(__name__)


def _persist_draft(
    db: Session,
    lead: BusinessLead,
    content: DraftContent,
    *,
    action: str,
) -> OutreachDraft:
    draft = OutreachDraft(
        business_lead_id=lead.id,
        tone=content.tone,
        subject_line=content.subject_line,
        email_body=content.email_body,
        short_dm=content.short_dm,
        call_notes=content.call_notes,
        status=OutreachDraftStatus.DRAFT_READY.value,
        primary_angle=content.primary_angle,
        context={
            "primary_angle_label": ANGLE_LABELS.get(content.primary_angle, content.primary_angle),
            "secondary_angles": content.secondary_angles,
            "findings_used": content.findings_used,
        },
    )
    db.add(draft)
    db.flush()
    log_action(
        db,
        action,
        "business_lead",
        lead.id,
        details={
            "draft_id": draft.id,
            "primary_angle": content.primary_angle,
            "findings": content.findings_used,
        },
    )
    db.commit()
    db.refresh(draft)
    logger.info(
        action,
        lead_id=lead.id,
        draft_id=draft.id,
        primary_angle=content.primary_angle,
    )
    return draft


def generate_draft(db: Session, lead_id: int, tone: str = "professional") -> OutreachDraft:
    """Create a new review-only outreach draft for a lead."""
    lead = get_lead(db, lead_id)
    if lead is None:
        raise ValueError(f"Lead {lead_id} not found")

    content = render_draft(
        lead,
        latest_inspection(lead),
        latest_score(lead),
        tone=tone,
    )
    return _persist_draft(db, lead, content, action="outreach_draft_created")


def regenerate_draft(db: Session, lead_id: int, tone: str = "professional") -> OutreachDraft:
    """Create a fresh draft record using latest lead data (preserves history)."""
    lead = get_lead(db, lead_id)
    if lead is None:
        raise ValueError(f"Lead {lead_id} not found")

    content = render_draft(
        lead,
        latest_inspection(lead),
        latest_score(lead),
        tone=tone,
    )
    return _persist_draft(db, lead, content, action="outreach_draft_regenerated")


def get_draft(db: Session, draft_id: int) -> OutreachDraft | None:
    return db.scalar(
        select(OutreachDraft)
        .where(OutreachDraft.id == draft_id)
        .options(selectinload(OutreachDraft.business_lead))
    )


def latest_draft_for_lead(db: Session, lead_id: int) -> OutreachDraft | None:
    return db.scalar(
        select(OutreachDraft)
        .where(OutreachDraft.business_lead_id == lead_id)
        .order_by(OutreachDraft.created_at.desc())
        .limit(1)
    )


def list_drafts(
    db: Session,
    *,
    lead_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[OutreachDraft]:
    stmt = select(OutreachDraft).order_by(OutreachDraft.created_at.desc())
    if lead_id is not None:
        stmt = stmt.where(OutreachDraft.business_lead_id == lead_id)
    if status:
        stmt = stmt.where(OutreachDraft.status == status)
    stmt = (
        stmt.offset(offset)
        .limit(limit)
        .options(selectinload(OutreachDraft.business_lead))
    )
    return list(db.scalars(stmt).unique().all())


def count_drafts(db: Session, status: str | None = None) -> int:
    stmt = select(func.count()).select_from(OutreachDraft)
    if status:
        stmt = stmt.where(OutreachDraft.status == status)
    return db.scalar(stmt) or 0


def update_draft_status(db: Session, draft_id: int, status: str) -> OutreachDraft:
    """Update draft status (draft_ready, reviewed, archived)."""
    allowed = {
        OutreachDraftStatus.DRAFT_READY.value,
        OutreachDraftStatus.REVIEWED.value,
        OutreachDraftStatus.ARCHIVED.value,
    }
    if status not in allowed:
        raise ValueError(f"Invalid status: {status}")

    draft = get_draft(db, draft_id)
    if draft is None:
        raise ValueError(f"Draft {draft_id} not found")

    draft.status = status
    db.flush()
    log_action(
        db,
        "outreach_draft_status_updated",
        "outreach_draft",
        draft.id,
        details={"status": status, "lead_id": draft.business_lead_id},
    )
    db.commit()
    db.refresh(draft)
    return draft


def mark_draft_reviewed(db: Session, draft_id: int) -> OutreachDraft:
    return update_draft_status(db, draft_id, OutreachDraftStatus.REVIEWED.value)


def archive_draft(db: Session, draft_id: int) -> OutreachDraft:
    return update_draft_status(db, draft_id, OutreachDraftStatus.ARCHIVED.value)
