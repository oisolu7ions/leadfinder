"""High-level enqueue helpers for background jobs."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.enums import ExportJobStatus, ScanJobStatus
from app.services.export_service import create_export_job, normalize_export_filters
from app.services.lead import list_uninspected_lead_ids
from app.services.scan import create_scan_job
from app.workers.job_types import JobType
from app.workers.queue import enqueue_job, enqueue_jobs, get_queue_length


def enqueue_scan_job(
    db: Session,
    scan_job_id: int,
    *,
    limit: int = 50,
    settings: Settings | None = None,
) -> int:
    return enqueue_job(
        JobType.SCAN,
        {"scan_job_id": scan_job_id, "limit": limit},
        settings=settings,
    )


def create_and_enqueue_scan(
    db: Session,
    category: str,
    city: str,
    source_name: str,
    state: str | None = None,
    *,
    limit: int = 50,
    settings: Settings | None = None,
) -> tuple[int, int]:
    """Create a pending ScanJob and enqueue it. Returns (scan_job_id, queue_length)."""
    job = create_scan_job(db, category, city, source_name, state)
    db.commit()
    qlen = enqueue_scan_job(db, job.id, limit=limit, settings=settings)
    return job.id, qlen


def enqueue_inspection(
    lead_id: int,
    *,
    auto_score: bool = True,
    settings: Settings | None = None,
) -> int:
    return enqueue_job(
        JobType.INSPECT,
        {"lead_id": lead_id, "auto_score": auto_score},
        settings=settings,
    )


def enqueue_inspections(
    lead_ids: list[int],
    *,
    auto_score: bool = True,
    settings: Settings | None = None,
) -> int:
    if not lead_ids:
        return get_queue_length(settings=settings)
    jobs = [
        (JobType.INSPECT, {"lead_id": lid, "auto_score": auto_score}) for lid in lead_ids
    ]
    return enqueue_jobs(jobs, settings=settings)


def enqueue_bulk_inspection(
    db: Session,
    *,
    uninspected_limit: int = 25,
    lead_ids: list[int] | None = None,
    auto_score: bool = True,
    settings: Settings | None = None,
) -> int:
    payload: dict = {"auto_score": auto_score}
    if lead_ids:
        payload["lead_ids"] = lead_ids
    else:
        payload["uninspected_limit"] = uninspected_limit
    return enqueue_job(JobType.INSPECT_BULK, payload, settings=settings)


def enqueue_score(lead_id: int, *, settings: Settings | None = None) -> int:
    return enqueue_job(JobType.SCORE, {"lead_id": lead_id}, settings=settings)


def enqueue_score_bulk(*, limit: int = 50, settings: Settings | None = None) -> int:
    return enqueue_job(JobType.SCORE_BULK, {"limit": limit}, settings=settings)


def enqueue_outreach(lead_id: int, *, settings: Settings | None = None) -> int:
    return enqueue_job(JobType.OUTREACH, {"lead_id": lead_id}, settings=settings)


def create_and_enqueue_export(
    db: Session,
    filters: dict,
    *,
    fmt: str = "csv",
    settings: Settings | None = None,
) -> tuple[int, int]:
    """Create pending ExportJob and enqueue. Returns (export_job_id, queue_length)."""
    snapshot = normalize_export_filters(filters)
    job = create_export_job(db, snapshot, fmt=fmt)
    db.commit()
    qlen = enqueue_job(JobType.EXPORT, {"export_job_id": job.id}, settings=settings)
    return job.id, qlen


def enqueue_export_job(export_job_id: int, *, settings: Settings | None = None) -> int:
    return enqueue_job(JobType.EXPORT, {"export_job_id": export_job_id}, settings=settings)
