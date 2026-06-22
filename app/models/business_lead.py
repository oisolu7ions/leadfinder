"""Business lead model — normalized business records from scans."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import LeadStatus

if TYPE_CHECKING:
    from app.models.lead_score import LeadScore
    from app.models.outreach_draft import OutreachDraft
    from app.models.scan_job import ScanJob
    from app.models.website_inspection import WebsiteInspection


class BusinessLead(TimestampMixin, Base):
    """A discovered business lead with contact and website metadata."""

    __tablename__ = "business_leads"
    __table_args__ = (
        UniqueConstraint("source_name", "external_id", name="uq_lead_source_external_id"),
        Index("ix_leads_dedup_name_city", "normalized_name", "city"),
        Index("ix_leads_dedup_phone", "phone"),
        Index("ix_leads_dedup_domain", "normalized_domain"),
        Index("ix_leads_dedup_address", "normalized_address_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("scan_jobs.id"),
        nullable=True,
        index=True,
    )

    source_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    business_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    normalized_name: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)

    phone: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    address_line1: Mapped[str | None] = mapped_column(String(500), nullable=True)
    normalized_address_key: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    city: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True, default="US")

    website_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    normalized_domain: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    social_links: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    status: Mapped[str] = mapped_column(
        String(50),
        default=LeadStatus.NEW.value,
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    scan_job: Mapped[ScanJob | None] = relationship(back_populates="business_leads")
    inspections: Mapped[list["WebsiteInspection"]] = relationship(
        back_populates="business_lead",
        order_by="desc(WebsiteInspection.inspected_at)",
    )
    scores: Mapped[list["LeadScore"]] = relationship(
        back_populates="business_lead",
        order_by="desc(LeadScore.scored_at)",
    )
    outreach_drafts: Mapped[list["OutreachDraft"]] = relationship(
        back_populates="business_lead",
        order_by="desc(OutreachDraft.created_at)",
    )

    def __repr__(self) -> str:
        return f"<BusinessLead id={self.id} name={self.business_name!r}>"
