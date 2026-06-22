"""CSV export job tracking."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import ExportFormat, ExportJobStatus


class ExportJob(TimestampMixin, Base):
    """Background export job with filter snapshot and output path."""

    __tablename__ = "export_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    format: Mapped[str] = mapped_column(
        String(20),
        default=ExportFormat.CSV.value,
        nullable=False,
    )
    filters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default=ExportJobStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<ExportJob id={self.id} format={self.format} status={self.status}>"
