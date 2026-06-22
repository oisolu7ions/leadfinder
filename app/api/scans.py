"""REST API for scan job ingestion."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.scan import ScanCreateRequest, ScanJobListResponse, ScanJobResponse
from app.services.scan import (
    create_and_run_scan,
    create_scan_job,
    get_scan_job,
    list_scan_jobs,
    run_scan_job,
)
from app.workers.enqueue import enqueue_scan_job

router = APIRouter(prefix="/api/scans", tags=["api-scans"])


@router.post("", response_model=ScanJobResponse, status_code=201)
def api_create_scan(
    body: ScanCreateRequest,
    db: Session = Depends(get_db),
) -> ScanJobResponse:
    """Create a scan job. Runs immediately when ``run_immediately`` is true (default)."""
    if body.run_immediately:
        job = create_and_run_scan(
            db,
            category=body.category,
            city=body.city,
            source_name=body.source_name,
            state=body.state,
            limit=body.limit,
            page=body.page,
        )
    else:
        job = create_scan_job(
            db,
            category=body.category,
            city=body.city,
            source_name=body.source_name,
            state=body.state,
        )
        db.commit()
        db.refresh(job)
        enqueue_scan_job(db, job.id, limit=body.limit)
    return ScanJobResponse.model_validate(job)


@router.post("/{job_id}/enqueue", response_model=ScanJobResponse, status_code=202)
def api_enqueue_scan(
    job_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
) -> ScanJobResponse:
    """Enqueue a pending scan job for background processing."""
    job = get_scan_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Scan job not found")
    enqueue_scan_job(db, job_id, limit=limit)
    return ScanJobResponse.model_validate(job)


@router.post("/{job_id}/run", response_model=ScanJobResponse)
def api_run_scan(
    job_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    page: int = Query(1, ge=1),
) -> ScanJobResponse:
    """Run a pending scan job manually."""
    try:
        job = run_scan_job(db, job_id, limit=limit, page=page)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        job = get_scan_job(db, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Scan job not found") from exc
        return ScanJobResponse.model_validate(job)
    return ScanJobResponse.model_validate(job)


@router.get("", response_model=ScanJobListResponse)
def api_list_scans(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
) -> ScanJobListResponse:
    jobs = list_scan_jobs(db, limit=limit)
    return ScanJobListResponse(
        items=[ScanJobResponse.model_validate(j) for j in jobs],
        total=len(jobs),
    )


@router.get("/{job_id}", response_model=ScanJobResponse)
def api_get_scan(job_id: int, db: Session = Depends(get_db)) -> ScanJobResponse:
    job = get_scan_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return ScanJobResponse.model_validate(job)
