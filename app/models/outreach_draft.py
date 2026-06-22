"""Outreach draft records — review-only, never auto-sent."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import OutreachDraftStatus

if TYPE_CHECKING:
    from app.models.business_lead import BusinessLead


class OutreachDraft(Base):
    """Template-based outreach draft for human review."""

    __tablename__ = "outreach_drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_lead_id: Mapped[int] = mapped_column(
        ForeignKey("business_leads.id"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    tone: Mapped[str] = mapped_column(String(50), default="professional", nullable=False)
    subject_line: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_dm: Mapped[str | None] = mapped_column(Text, nullable=True)
    call_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default=OutreachDraftStatus.DRAFT_READY.value,
        nullable=False,
        index=True,
    )
    primary_angle: Mapped[str | None] = mapped_column(String(80), nullable=True)
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    business_lead: Mapped[BusinessLead] = relationship(back_populates="outreach_drafts")

    def __repr__(self) -> str:
        return f"<OutreachDraft id={self.id} lead_id={self.business_lead_id} status={self.status}>"
