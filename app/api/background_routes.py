"""Background job enqueue and schedule REST API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.background import (
    BulkInspectionEnqueueRequest,
    BulkScoreEnqueueRequest,
    EnqueueResponse,
    ExportEnqueueRequest,
    QueueStatsResponse,
    ScanEnqueueRequest,
    ScheduledTaskCreateRequest,
    ScheduledTaskListResponse,
    ScheduledTaskResponse,
    ScheduledTaskUpdateRequest,
)
from app.scheduler.service import (
    create_scheduled_task,
    get_scheduled_task,
    list_scheduled_tasks,
    update_scheduled_task,
)
from app.services.lead import get_lead
from app.services.scan import get_scan_job
from app.workers.enqueue import (
    create_and_enqueue_export,
    create_and_enqueue_scan,
    enqueue_bulk_inspection,
    enqueue_export_job,
    enqueue_inspection,
    enqueue_outreach,
    enqueue_scan_job,
    enqueue_score,
    enqueue_score_bulk,
)
from app.workers.queue import get_queue_stats

router = APIRouter(prefix="/api/background", tags=["background"])


@router.get("/queue", response_model=QueueStatsResponse)
def api_queue_stats() -> QueueStatsResponse:
    stats = get_queue_stats()
    return QueueStatsResponse(**stats)


@router.post("/scans", response_model=EnqueueResponse, status_code=202)
def api_enqueue_scan(body: ScanEnqueueRequest, db: Session = Depends(get_db)) -> EnqueueResponse:
    job_id, qlen = create_and_enqueue_scan(
        db,
        body.category,
        body.city,
        body.source_name,
        body.state,
        limit=body.limit,
    )
    return EnqueueResponse(queued=1, queue_length=qlen, job_id=job_id, mode="queued")


@router.post("/scans/{job_id}/enqueue", response_model=EnqueueResponse, status_code=202)
def api_enqueue_existing_scan(
    job_id: int,
    db: Session = Depends(get_db),
    limit: int = 50,
) -> EnqueueResponse:
    if get_scan_job(db, job_id) is None:
        raise HTTPException(status_code=404, detail="Scan job not found")
    qlen = enqueue_scan_job(db, job_id, limit=limit)
    return EnqueueResponse(queued=1, queue_length=qlen, job_id=job_id, mode="queued")


@router.post("/inspections/leads/{lead_id}", response_model=EnqueueResponse, status_code=202)
def api_enqueue_inspection(lead_id: int, db: Session = Depends(get_db)) -> EnqueueResponse:
    if get_lead(db, lead_id) is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    qlen = enqueue_inspection(lead_id)
    return EnqueueResponse(queued=1, queue_length=qlen, job_id=lead_id, mode="queued")


@router.post("/inspections/bulk", response_model=EnqueueResponse, status_code=202)
def api_enqueue_bulk_inspection(
    body: BulkInspectionEnqueueRequest,
    db: Session = Depends(get_db),
) -> EnqueueResponse:
    if not body.lead_ids and not body.uninspected_limit:
        raise HTTPException(
            status_code=400,
            detail="Provide lead_ids and/or uninspected_limit",
        )
    qlen = enqueue_bulk_inspection(
        db,
        uninspected_limit=body.uninspected_limit or 25,
        lead_ids=body.lead_ids or None,
        auto_score=body.auto_score,
    )
    count = len(body.lead_ids) if body.lead_ids else (body.uninspected_limit or 25)
    return EnqueueResponse(queued=count, queue_length=qlen, mode="queued")


@router.post("/scoring/leads/{lead_id}", response_model=EnqueueResponse, status_code=202)
def api_enqueue_score(lead_id: int, db: Session = Depends(get_db)) -> EnqueueResponse:
    if get_lead(db, lead_id) is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    qlen = enqueue_score(lead_id)
    return EnqueueResponse(queued=1, queue_length=qlen, job_id=lead_id, mode="queued")


@router.post("/scoring/bulk/unscored", response_model=EnqueueResponse, status_code=202)
def api_enqueue_score_bulk(body: BulkScoreEnqueueRequest) -> EnqueueResponse:
    qlen = enqueue_score_bulk(limit=body.limit)
    return EnqueueResponse(queued=body.limit, queue_length=qlen, mode="queued")


@router.post("/outreach/leads/{lead_id}", response_model=EnqueueResponse, status_code=202)
def api_enqueue_outreach(lead_id: int, db: Session = Depends(get_db)) -> EnqueueResponse:
    if get_lead(db, lead_id) is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    qlen = enqueue_outreach(lead_id)
    return EnqueueResponse(queued=1, queue_length=qlen, job_id=lead_id, mode="queued")


@router.post("/exports", response_model=EnqueueResponse, status_code=202)
def api_enqueue_export(body: ExportEnqueueRequest, db: Session = Depends(get_db)) -> EnqueueResponse:
    job_id, qlen = create_and_enqueue_export(db, body.filters, fmt=body.format)
    return EnqueueResponse(queued=1, queue_length=qlen, job_id=job_id, mode="queued")


@router.post("/exports/{job_id}/enqueue", response_model=EnqueueResponse, status_code=202)
def api_enqueue_existing_export(job_id: int, db: Session = Depends(get_db)) -> EnqueueResponse:
    from app.services.export_service import get_export_job

    if get_export_job(db, job_id) is None:
        raise HTTPException(status_code=404, detail="Export job not found")
    qlen = enqueue_export_job(job_id)
    return EnqueueResponse(queued=1, queue_length=qlen, job_id=job_id, mode="queued")


@router.get("/schedules", response_model=ScheduledTaskListResponse)
def api_list_schedules(db: Session = Depends(get_db)) -> ScheduledTaskListResponse:
    tasks = list_scheduled_tasks(db)
    return ScheduledTaskListResponse(
        items=[ScheduledTaskResponse.model_validate(t) for t in tasks],
        total=len(tasks),
    )


@router.post("/schedules", response_model=ScheduledTaskResponse, status_code=201)
def api_create_schedule(
    body: ScheduledTaskCreateRequest,
    db: Session = Depends(get_db),
) -> ScheduledTaskResponse:
    try:
        task = create_scheduled_task(
            db,
            name=body.name,
            task_type=body.task_type,
            interval_minutes=body.interval_minutes,
            payload=body.payload,
            enabled=body.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ScheduledTaskResponse.model_validate(task)


@router.patch("/schedules/{task_id}", response_model=ScheduledTaskResponse)
def api_update_schedule(
    task_id: int,
    body: ScheduledTaskUpdateRequest,
    db: Session = Depends(get_db),
) -> ScheduledTaskResponse:
    try:
        task = update_scheduled_task(
            db,
            task_id,
            enabled=body.enabled,
            interval_minutes=body.interval_minutes,
            payload=body.payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ScheduledTaskResponse.model_validate(task)


@router.get("/schedules/{task_id}", response_model=ScheduledTaskResponse)
def api_get_schedule(task_id: int, db: Session = Depends(get_db)) -> ScheduledTaskResponse:
    task = get_scheduled_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Scheduled task not found")
    return ScheduledTaskResponse.model_validate(task)
