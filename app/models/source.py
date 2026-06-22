"""Data source registry — tracks configured lead providers."""

from sqlalchemy import Boolean, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Source(TimestampMixin, Base):
    """Registered lead data source (e.g. mock, tomtom, google_places)."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    scan_jobs: Mapped[list["ScanJob"]] = relationship(back_populates="source_ref")

    def __repr__(self) -> str:
        return f"<Source id={self.id} name={self.name!r}>"
