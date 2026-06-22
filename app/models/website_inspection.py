"""Website inspection results for a business lead."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.business_lead import BusinessLead


class WebsiteInspection(Base):
    """Heuristic and optional browser-based website inspection record."""

    __tablename__ = "website_inspections"

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
    inspected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    final_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reachable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    blank_website: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    social_only: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    branded_domain: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    mobile_friendly_basic: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_contact_page: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_booking_flow: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ssl_present: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    page_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    technologies: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    html_snapshot_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    findings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    business_lead: Mapped[BusinessLead] = relationship(back_populates="inspections")

    def __repr__(self) -> str:
        return f"<WebsiteInspection id={self.id} lead_id={self.business_lead_id}>"
