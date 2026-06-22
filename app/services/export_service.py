"""CSV export generation and ExportJob management."""

from __future__ import annotations

import csv
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.business_lead import BusinessLead
from app.models.enums import ExportFormat, ExportJobStatus
from app.models.export_job import ExportJob
from app.services.audit import log_action
from app.services.export_serializers import EXPORT_CSV_COLUMNS, lead_to_export_row, row_to_csv_values
from app.services.lead import LeadFilters, build_leads_query
from app.utils.file_storage import export_filename

logger = get_logger(__name__)

EXPORT_FILTER_KEYS = (
    "search",
    "city",
    "state",
    "category",
    "source_name",
    "status",
    "has_website",
    "social_only",
    "min_score",
    "max_score",
    "inspected",
    "outreach_status",
    "priority",
    "insp_reachable",
    "insp_blank_website",
    "insp_social_only",
    "insp_has_contact_page",
    "insp_has_booking_flow",
)


def lead_filters_from_dict(data: dict, *, per_page: int = 10_000) -> LeadFilters:
    """Build LeadFilters from a plain dict (export form / API body)."""
    min_score = data.get("min_score")
    max_score = data.get("max_score")
    return LeadFilters(
        search=data.get("search") or None,
        city=data.get("city") or None,
        state=data.get("state") or None,
        category=data.get("category") or None,
        source_name=data.get("source_name") or None,
        status=data.get("status") or None,
        has_website=data.get("has_website") or None,
        social_only=data.get("social_only") or None,
        min_score=int(min_score) if min_score not in (None, "") else None,
        max_score=int(max_score) if max_score not in (None, "") else None,
        inspected=data.get("inspected") or None,
        outreach_status=data.get("outreach_status") or None,
        priority=data.get("priority") or None,
        insp_reachable=data.get("insp_reachable") or None,
        insp_blank_website=data.get("insp_blank_website") or None,
        insp_social_only=data.get("insp_social_only") or None,
        insp_has_contact_page=data.get("insp_has_contact_page") or None,
        insp_has_booking_flow=data.get("insp_has_booking_flow") or None,
        page=1,
        per_page=per_page,
    )


def normalize_export_filters(data: dict) -> dict:
    """Keep only recognized non-empty filter keys."""
    return {k: v for k, v in data.items() if k in EXPORT_FILTER_KEYS and v not in (None, "")}


def filters_summary(filters: dict | None) -> str:
    """Human-readable one-line filter summary for UI."""
    if not filters:
        return "All leads"
    parts = [f"{k}={v}" for k, v in sorted(filters.items())]
    summary = ", ".join(parts)
    return summary if len(summary) <= 120 else summary[:117] + "..."


def create_export_job(
    db: Session,
    filters: dict,
    fmt: str = ExportFormat.CSV.value,
) -> ExportJob:
    """Create a pending export job."""
    snapshot = normalize_export_filters(filters)
    job = ExportJob(format=fmt, filters=snapshot, status=ExportJobStatus.PENDING.value)
    db.add(job)
    db.flush()
    log_action(db, "export_created", "export_job", job.id, details={"filters": snapshot})
    return job


def query_leads_for_export(db: Session, filters: LeadFilters) -> list[BusinessLead]:
    stmt = (
        build_leads_query(filters)
        .order_by(BusinessLead.updated_at.desc())
        .options(
            selectinload(BusinessLead.scores),
            selectinload(BusinessLead.inspections),
            selectinload(BusinessLead.outreach_drafts),
        )
    )
    return list(db.scalars(stmt).unique().all())


def write_leads_csv(filepath, leads: list[BusinessLead]) -> int:
    """Write leads to CSV; return row count."""
    with filepath.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(EXPORT_CSV_COLUMNS)
        for lead in leads:
            writer.writerow(row_to_csv_values(lead_to_export_row(lead)))
    return len(leads)


def run_export_job(db: Session, job_id: int, settings: Settings | None = None) -> ExportJob:
    """Generate a CSV export synchronously."""
    settings = settings or get_settings()
    job = db.get(ExportJob, job_id)
    if job is None:
        raise ValueError(f"Export job {job_id} not found")

    job.status = ExportJobStatus.RUNNING.value
    job.started_at = datetime.now(UTC)
    job.error_message = None
    db.flush()

    try:
        settings.export_dir.mkdir(parents=True, exist_ok=True)
        filters = lead_filters_from_dict(job.filters or {})
        leads = query_leads_for_export(db, filters)

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = export_filename(job.id, timestamp)
        filepath = settings.export_dir / filename

        row_count = write_leads_csv(filepath, leads)

        job.file_path = filename
        job.row_count = row_count
        job.status = ExportJobStatus.COMPLETED.value
        job.finished_at = datetime.now(UTC)
        log_action(
            db,
            "export_completed",
            "export_job",
            job.id,
            details={"rows": row_count, "file": filename},
        )
        logger.info("export_completed", job_id=job.id, rows=row_count, file=str(filepath))
    except Exception as exc:
        job.status = ExportJobStatus.FAILED.value
        job.error_message = str(exc)
        job.finished_at = datetime.now(UTC)
        log_action(db, "export_failed", "export_job", job.id, details={"error": str(exc)})
        logger.exception("export_failed", job_id=job.id)
        db.commit()
        raise

    db.commit()
    db.refresh(job)
    return job


def get_export_job(db: Session, job_id: int) -> ExportJob | None:
    return db.get(ExportJob, job_id)


def list_export_jobs(db: Session, limit: int = 50) -> list[ExportJob]:
    return list(
        db.scalars(
            select(ExportJob).order_by(ExportJob.created_at.desc()).limit(limit)
        ).all()
    )
