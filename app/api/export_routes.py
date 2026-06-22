"""Export job REST API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import Settings, get_settings
from app.schemas.export import ExportCreateRequest, ExportJobListResponse, ExportJobResponse
from app.services.export_service import (
    create_export_job,
    filters_summary,
    get_export_job,
    list_export_jobs,
    normalize_export_filters,
    run_export_job,
)
from app.utils.file_storage import ExportFileError, resolve_export_download_path

router = APIRouter(prefix="/api/exports", tags=["exports"])


def _to_response(job) -> ExportJobResponse:
    return ExportJobResponse(
        id=job.id,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        format=job.format,
        filters=job.filters,
        filters_summary=filters_summary(job.filters),
        file_path=job.file_path,
        status=job.status,
        error_message=job.error_message,
        row_count=job.row_count,
    )


@router.post("", response_model=ExportJobResponse)
def api_create_export(
    body: ExportCreateRequest,
    db: Session = Depends(get_db),
) -> ExportJobResponse:
    from app.workers.enqueue import create_and_enqueue_export

    filters = normalize_export_filters(body.filters)
    if body.run_immediately:
        job = create_export_job(db, filters, fmt=body.format)
        db.commit()
        try:
            job = run_export_job(db, job.id)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    else:
        job_id, _ = create_and_enqueue_export(db, filters, fmt=body.format)
        job = get_export_job(db, job_id)
        if job is None:
            raise HTTPException(status_code=500, detail="Export job not found after enqueue")
    return _to_response(job)


@router.get("", response_model=ExportJobListResponse)
def api_list_exports(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
) -> ExportJobListResponse:
    jobs = list_export_jobs(db, limit=limit)
    return ExportJobListResponse(items=[_to_response(j) for j in jobs], total=len(jobs))


@router.get("/{job_id}", response_model=ExportJobResponse)
def api_get_export(job_id: int, db: Session = Depends(get_db)) -> ExportJobResponse:
    job = get_export_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Export job {job_id} not found")
    return _to_response(job)


@router.get("/{job_id}/download")
def api_download_export(
    job_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    job = get_export_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Export job {job_id} not found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Export is not ready (status: {job.status})")
    try:
        path = resolve_export_download_path(settings.export_dir, job)
    except ExportFileError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(
        path=path,
        filename=path.name,
        media_type="text/csv",
    )
