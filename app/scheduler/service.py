"""Scheduled task CRUD and tick logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.scheduled_task import ScheduledTask
from app.services.audit import log_action
from app.services.export_service import create_export_job, normalize_export_filters
from app.services.scan import create_scan_job
from app.workers.enqueue import (
    enqueue_bulk_inspection,
    enqueue_export_job,
    enqueue_scan_job,
    enqueue_score_bulk,
)
from app.workers.job_types import ScheduledTaskType

logger = get_logger(__name__)


def list_scheduled_tasks(db: Session, *, enabled_only: bool = False) -> list[ScheduledTask]:
    stmt = select(ScheduledTask).order_by(ScheduledTask.name)
    if enabled_only:
        stmt = stmt.where(ScheduledTask.enabled.is_(True))
    return list(db.scalars(stmt).all())


def get_scheduled_task(db: Session, task_id: int) -> ScheduledTask | None:
    return db.get(ScheduledTask, task_id)


def create_scheduled_task(
    db: Session,
    *,
    name: str,
    task_type: str,
    interval_minutes: int,
    payload: dict | None = None,
    enabled: bool = True,
) -> ScheduledTask:
    now = datetime.now(UTC)
    task = ScheduledTask(
        name=name,
        task_type=task_type,
        interval_minutes=interval_minutes,
        payload=payload or {},
        enabled=enabled,
        next_run_at=now,
        last_status="pending",
    )
    db.add(task)
    db.flush()
    log_action(db, "scheduled_task_created", "scheduled_task", task.id)
    db.commit()
    db.refresh(task)
    return task


def update_scheduled_task(
    db: Session,
    task_id: int,
    *,
    enabled: bool | None = None,
    interval_minutes: int | None = None,
    payload: dict | None = None,
) -> ScheduledTask:
    task = get_scheduled_task(db, task_id)
    if task is None:
        raise ValueError(f"Scheduled task {task_id} not found")
    if enabled is not None:
        task.enabled = enabled
    if interval_minutes is not None:
        task.interval_minutes = interval_minutes
    if payload is not None:
        task.payload = payload
    db.commit()
    db.refresh(task)
    return task


def _enqueue_from_task(db: Session, task: ScheduledTask) -> None:
    payload = task.payload or {}
    if task.task_type == ScheduledTaskType.SCAN.value:
        job = create_scan_job(
            db,
            payload["category"],
            payload["city"],
            payload.get("source_name", "mock"),
            payload.get("state"),
        )
        db.commit()
        enqueue_scan_job(db, job.id, limit=int(payload.get("limit", 50)))
    elif task.task_type == ScheduledTaskType.INSPECT_UNREVIEWED.value:
        enqueue_bulk_inspection(
            db,
            uninspected_limit=int(payload.get("uninspected_limit", 25)),
            auto_score=bool(payload.get("auto_score", True)),
        )
    elif task.task_type == ScheduledTaskType.SCORE_UNSCORED.value:
        enqueue_score_bulk(limit=int(payload.get("limit", 50)))
    elif task.task_type == ScheduledTaskType.EXPORT.value:
        filters = normalize_export_filters(payload.get("filters") or {})
        export_job = create_export_job(db, filters)
        db.commit()
        enqueue_export_job(export_job.id)
    else:
        raise ValueError(f"Unknown scheduled task type: {task.task_type}")


def run_due_scheduled_tasks(db: Session) -> list[ScheduledTask]:
    """Find due tasks, enqueue jobs, update schedule metadata."""
    now = datetime.now(UTC)
    due = list(
        db.scalars(
            select(ScheduledTask)
            .where(ScheduledTask.enabled.is_(True))
            .where(ScheduledTask.next_run_at.isnot(None))
            .where(ScheduledTask.next_run_at <= now)
        ).all()
    )
    ran: list[ScheduledTask] = []
    for task in due:
        task.last_status = "running"
        db.flush()
        try:
            _enqueue_from_task(db, task)
            task.last_run_at = now
            task.next_run_at = now + timedelta(minutes=task.interval_minutes)
            task.last_status = "completed"
            task.last_error = None
            logger.info("scheduled_task_enqueued", task_id=task.id, task_type=task.task_type)
        except Exception as exc:
            task.last_run_at = now
            task.next_run_at = now + timedelta(minutes=task.interval_minutes)
            task.last_status = "failed"
            task.last_error = str(exc)
            logger.exception("scheduled_task_failed", task_id=task.id)
        ran.append(task)
    if ran:
        db.commit()
    return ran
