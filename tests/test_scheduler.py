"""Tests for scheduled task service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.db.session import get_session_factory, reset_engine
from app.models.scheduled_task import ScheduledTask
from app.scheduler.service import create_scheduled_task, run_due_scheduled_tasks
from app.services.scan import ensure_default_sources
from app.workers.job_types import ScheduledTaskType


@pytest.fixture
def db() -> Session:
    reset_engine()
    session = get_session_factory()()
    ensure_default_sources(session)
    yield session
    session.close()
    reset_engine()


def test_create_scheduled_task(db: Session) -> None:
    task = create_scheduled_task(
        db,
        name="Test scan",
        task_type=ScheduledTaskType.SCAN.value,
        interval_minutes=60,
        payload={"category": "dentist", "city": "Austin", "source_name": "mock"},
    )
    assert task.id is not None
    assert task.enabled is True
    assert task.next_run_at is not None


def test_run_due_tasks_enqueues_scan(db: Session) -> None:
    now = datetime.now(UTC)
    task = ScheduledTask(
        name="Due scan",
        task_type=ScheduledTaskType.SCAN.value,
        enabled=True,
        interval_minutes=30,
        payload={"category": "cafe", "city": "Miami", "source_name": "mock", "limit": 5},
        next_run_at=now - timedelta(minutes=1),
    )
    db.add(task)
    db.commit()

    with patch("app.scheduler.service.enqueue_scan_job") as mock_enqueue:
        mock_enqueue.return_value = 1
        ran = run_due_scheduled_tasks(db)

    our_runs = [t for t in ran if t.id == task.id]
    assert len(our_runs) == 1
    assert our_runs[0].last_status == "completed"
    mock_enqueue.assert_called()


def test_run_due_skips_future_tasks(db: Session) -> None:
    future = datetime.now(UTC) + timedelta(hours=1)
    task = ScheduledTask(
        name="Future",
        task_type=ScheduledTaskType.SCORE_UNSCORED.value,
        enabled=True,
        interval_minutes=60,
        payload={"limit": 10},
        next_run_at=future,
    )
    db.add(task)
    db.commit()

    with patch("app.scheduler.service.enqueue_score_bulk") as mock_enqueue:
        ran = run_due_scheduled_tasks(db)

    assert ran == []
    mock_enqueue.assert_not_called()
