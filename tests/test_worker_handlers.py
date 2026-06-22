"""Tests for background job handlers."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.db.session import get_session_factory, reset_engine
from app.services.scan import create_scan_job, ensure_default_sources
from app.workers.jobs.handlers import handle_job
from app.workers.job_types import JobType
from app.workers.queue import JobEnvelope


@pytest.fixture
def db() -> Session:
    reset_engine()
    session = get_session_factory()()
    ensure_default_sources(session)
    yield session
    session.close()
    reset_engine()


def test_handle_scan_calls_run_scan_job(db: Session) -> None:
    job = create_scan_job(db, "cafe", "Denver", "mock", "CO")
    db.commit()
    envelope = JobEnvelope(type=JobType.SCAN.value, payload={"scan_job_id": job.id, "limit": 10})
    with patch("app.workers.jobs.handlers.run_scan_job") as mock_run:
        handle_job(db, envelope)
    mock_run.assert_called_once_with(db, job.id, limit=10)


def test_handle_inspect_calls_inspect_lead(db: Session) -> None:
    envelope = JobEnvelope(type=JobType.INSPECT.value, payload={"lead_id": 1, "auto_score": False})
    with patch("app.workers.jobs.handlers.inspect_lead") as mock_inspect:
        handle_job(db, envelope)
    mock_inspect.assert_called_once_with(db, 1, run_browser=None, auto_score=False)


def test_handle_export_calls_run_export_job(db: Session) -> None:
    envelope = JobEnvelope(type=JobType.EXPORT.value, payload={"export_job_id": 5})
    with patch("app.workers.jobs.handlers.run_export_job") as mock_export:
        handle_job(db, envelope)
    mock_export.assert_called_once_with(db, 5)


def test_unknown_job_type_raises(db: Session) -> None:
    envelope = JobEnvelope(type="unknown", payload={})
    with pytest.raises(ValueError, match="Unknown job type"):
        handle_job(db, envelope)
