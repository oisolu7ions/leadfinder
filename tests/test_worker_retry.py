"""Tests for worker retry requeue behavior."""

from unittest.mock import MagicMock

from app.workers.job_types import JobType
from app.workers.queue import JobEnvelope, requeue_job


def test_requeue_increments_attempt_until_max() -> None:
    mock_client = MagicMock()
    mock_client.rpush.return_value = 1
    envelope = JobEnvelope(
        type=JobType.EXPORT.value,
        payload={"export_job_id": 9},
        attempt=2,
        max_attempts=3,
    )
    requeue_job(envelope, client=mock_client)
    retry = JobEnvelope.from_raw(mock_client.rpush.call_args[0][1])
    assert retry.attempt == 3
