"""Tests for unified Redis job queue."""

from unittest.mock import MagicMock

import pytest

from app.workers.job_types import JobType
from app.workers.queue import (
    JobEnvelope,
    dequeue_job,
    enqueue_job,
    get_queue_length,
    get_queue_stats,
    requeue_job,
)


@pytest.fixture
def mock_redis() -> MagicMock:
    client = MagicMock()
    client.rpush.return_value = 1
    client.llen.return_value = 0
    client.lpop.return_value = None
    client.blpop.return_value = None
    return client


def test_enqueue_job_pushes_json(mock_redis: MagicMock) -> None:
    length = enqueue_job(JobType.INSPECT, {"lead_id": 42}, client=mock_redis)
    assert length == 1
    mock_redis.rpush.assert_called_once()
    raw = mock_redis.rpush.call_args[0][1]
    envelope = JobEnvelope.from_raw(raw)
    assert envelope.type == JobType.INSPECT.value
    assert envelope.payload["lead_id"] == 42


def test_legacy_payload_parsed_as_inspect() -> None:
    envelope = JobEnvelope.from_raw('{"lead_id": 7}')
    assert envelope.type == JobType.INSPECT.value
    assert envelope.payload["lead_id"] == 7


def test_dequeue_drains_legacy_first(mock_redis: MagicMock) -> None:
    mock_redis.lpop.return_value = b'{"lead_id": 3}'
    envelope = dequeue_job(client=mock_redis, block_seconds=1)
    assert envelope is not None
    assert envelope.payload["lead_id"] == 3
    mock_redis.blpop.assert_not_called()


def test_requeue_increments_attempt(mock_redis: MagicMock) -> None:
    envelope = JobEnvelope(type=JobType.EXPORT.value, payload={"export_job_id": 1}, attempt=1)
    requeue_job(envelope, client=mock_redis)
    raw = mock_redis.rpush.call_args[0][1]
    retry = JobEnvelope.from_raw(raw)
    assert retry.attempt == 2


def test_dequeue_returns_none_on_blpop_timeout(mock_redis: MagicMock) -> None:
    import redis

    mock_redis.lpop.return_value = None
    mock_redis.blpop.side_effect = redis.TimeoutError("Timeout reading from socket")
    assert dequeue_job(client=mock_redis, block_seconds=1) is None

    mock_redis.llen.side_effect = [2, 1]
    stats = get_queue_stats(client=mock_redis)
    assert stats["unified_queue"] == 2
    assert stats["legacy_inspection_queue"] == 1
    assert stats["total"] == 3
