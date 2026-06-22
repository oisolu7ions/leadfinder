"""Scan job creation and execution."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.enums import ScanJobStatus
from app.models.scan_job import ScanJob
from app.models.source import Source
from app.providers.registry import get_provider
from app.providers.scan_limits import effective_scan_limit, is_live_provider
from app.services.audit import log_action
from app.services.lead_persistence import upsert_lead

logger = get_logger(__name__)


def ensure_default_sources(db: Session) -> None:
    """Seed built-in providers into the sources table."""
    from app.providers.registry import list_providers

    for provider in list_providers():
        existing = db.scalar(select(Source).where(Source.name == provider.name))
        if existing:
            continue
        db.add(
            Source(
                name=provider.name,
                display_name=provider.display_name,
                description=f"Built-in {provider.display_name} provider",
                is_active=True,
            )
        )
    db.commit()


def create_scan_job(
    db: Session,
    category: str,
    city: str,
    source_name: str,
    state: str | None = None,
    query_text: str | None = None,
) -> ScanJob:
    """Create a pending scan job record."""
    source = db.scalar(select(Source).where(Source.name == source_name))
    job = ScanJob(
        category=category.strip(),
        city=city.strip(),
        state=state.strip() if state else None,
        query_text=query_text or f"{category} in {city}" + (f", {state}" if state else ""),
        source_name=source_name,
        source_id=source.id if source else None,
        status=ScanJobStatus.PENDING.value,
    )
    db.add(job)
    db.flush()
    log_action(db, "scan_created", "scan_job", job.id, details={"source": source_name})
    return job


def run_scan_job(db: Session, job_id: int, limit: int = 50, page: int = 1) -> ScanJob:
    """Execute a scan job synchronously against its provider."""
    job = db.get(ScanJob, job_id)
    if job is None:
        raise ValueError(f"Scan job {job_id} not found")

    job.status = ScanJobStatus.RUNNING.value
    job.started_at = datetime.now(UTC)
    db.flush()

    limit = effective_scan_limit(job.source_name, limit)

    logger.info(
        "scan_job_started",
        job_id=job_id,
        category=job.category,
        city=job.city,
        source=job.source_name,
        limit=limit,
        live=is_live_provider(job.source_name),
    )

    inserted = updated = flagged = 0
    error_message: str | None = None

    try:
        provider = get_provider(job.source_name)
        result = provider.search_businesses(
            category=job.category,
            city=job.city,
            state=job.state,
            limit=limit,
            page=page,
        )
        job.total_found = len(result.records)

        for record in result.records:
            lead, is_new = upsert_lead(db, record, job.source_name, scan_job_id=job.id)
            if is_new:
                inserted += 1
            else:
                updated += 1
            if not lead.website_url:
                flagged += 1

        job.total_inserted = inserted
        job.total_updated = updated
        job.total_flagged = flagged
        job.status = ScanJobStatus.COMPLETED.value
        job.logs_summary = (
            f"Provider returned {len(result.records)} record(s); "
            f"inserted {inserted}, updated {updated}, flagged (no website) {flagged}"
            + (f"; live scan limit {limit}" if is_live_provider(job.source_name) else "")
        )
        logger.info(
            "scan_job_completed",
            job_id=job_id,
            inserted=inserted,
            updated=updated,
            flagged=flagged,
        )
        log_action(
            db,
            "scan_completed",
            "scan_job",
            job.id,
            details={"inserted": inserted, "updated": updated, "flagged": flagged},
        )
    except Exception as exc:
        logger.exception("scan_job_failed", job_id=job_id)
        job.status = ScanJobStatus.FAILED.value
        job.error_message = str(exc)
        log_action(db, "scan_failed", "scan_job", job.id, details={"error": str(exc)})
        error_message = str(exc)

    job.finished_at = datetime.now(UTC)
    db.commit()
    db.refresh(job)

    if error_message:
        raise RuntimeError(error_message)

    return job


def create_and_run_scan(
    db: Session,
    category: str,
    city: str,
    source_name: str,
    state: str | None = None,
    limit: int = 50,
    page: int = 1,
) -> ScanJob:
    """Create a scan job and execute it immediately."""
    job = create_scan_job(db, category, city, source_name, state)
    db.commit()
    return run_scan_job(db, job.id, limit=limit, page=page)


def list_scan_jobs(db: Session, limit: int = 50) -> list[ScanJob]:
    """Return recent scan jobs."""
    return list(
        db.scalars(select(ScanJob).order_by(ScanJob.created_at.desc()).limit(limit)).all()
    )


def get_scan_job(db: Session, job_id: int) -> ScanJob | None:
    """Load a scan job with related leads."""
    from sqlalchemy.orm import selectinload

    return db.scalar(
        select(ScanJob)
        .where(ScanJob.id == job_id)
        .options(selectinload(ScanJob.business_leads))
    )
