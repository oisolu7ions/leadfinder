"""Scan job model — tracks category+city search runs."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import ScanJobStatus

if TYPE_CHECKING:
    from app.models.business_lead import BusinessLead
    from app.models.source import Source


class ScanJob(TimestampMixin, Base):
    """A single lead ingestion run for a category + location."""

    __tablename__ = "scan_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    category: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    query_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True)

    status: Mapped[str] = mapped_column(
        String(50),
        default=ScanJobStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    total_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_flagged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    logs_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_ref: Mapped[Source | None] = relationship(back_populates="scan_jobs")
    business_leads: Mapped[list["BusinessLead"]] = relationship(back_populates="scan_job")

    def __repr__(self) -> str:
        return f"<ScanJob id={self.id} {self.category!r} @ {self.city!r} status={self.status}>"
