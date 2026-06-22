"""Rule-based lead scoring records."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.business_lead import BusinessLead


class LeadScore(Base):
    """Transparent, explainable rule-based score for a business lead."""

    __tablename__ = "lead_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_lead_id: Mapped[int] = mapped_column(
        ForeignKey("business_leads.id"),
        nullable=False,
        index=True,
    )
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    total_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    no_website_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    outdated_website_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mobile_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    branding_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reachability_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ssl_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    contact_flow_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    social_only_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    business_lead: Mapped[BusinessLead] = relationship(back_populates="scores")

    def __repr__(self) -> str:
        return f"<LeadScore id={self.id} lead_id={self.business_lead_id} total={self.total_score}>"
