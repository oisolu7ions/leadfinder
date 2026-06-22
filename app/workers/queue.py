"""Generic Redis-backed job queue."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import redis

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.db.redis import get_redis_client
from app.workers.job_types import JobType

logger = get_logger(__name__)


@dataclass
class JobEnvelope:
    type: str
    payload: dict[str, Any]
    attempt: int = 1
    max_attempts: int = 3

    def to_json(self) -> str:
        return json.dumps(
            {
                "type": self.type,
                "payload": self.payload,
                "attempt": self.attempt,
                "max_attempts": self.max_attempts,
            }
        )

    @classmethod
    def from_raw(cls, raw: str) -> JobEnvelope:
        data = json.loads(raw)
        # Legacy inspection queue: {"lead_id": N}
        if "type" not in data and "lead_id" in data:
            return cls(
                type=JobType.INSPECT.value,
                payload={"lead_id": int(data["lead_id"])},
                attempt=int(data.get("attempt", 1)),
                max_attempts=int(data.get("max_attempts", 3)),
            )
        return cls(
            type=str(data["type"]),
            payload=dict(data.get("payload") or {}),
            attempt=int(data.get("attempt", 1)),
            max_attempts=int(data.get("max_attempts", 3)),
        )


def _queue_key(settings: Settings) -> str:
    return settings.job_queue_name


def _legacy_inspection_key(settings: Settings) -> str:
    return settings.inspection_queue_name


def enqueue_job(
    job_type: str | JobType,
    payload: dict[str, Any],
    *,
    attempt: int = 1,
    max_attempts: int | None = None,
    settings: Settings | None = None,
    client: redis.Redis | None = None,
) -> int:
    """Push a job onto the unified queue. Returns queue length."""
    settings = settings or get_settings()
    client = client or get_redis_client()
    envelope = JobEnvelope(
        type=str(job_type),
        payload=payload,
        attempt=attempt,
        max_attempts=max_attempts or settings.job_max_retries,
    )
    length = client.rpush(_queue_key(settings), envelope.to_json())
    logger.info("job_enqueued", job_type=envelope.type, payload=payload, queue_length=length)
    return int(length)


def enqueue_jobs(
    jobs: list[tuple[str | JobType, dict[str, Any]]],
    *,
    settings: Settings | None = None,
    client: redis.Redis | None = None,
) -> int:
    if not jobs:
        return get_queue_length(settings=settings, client=client)
    settings = settings or get_settings()
    client = client or get_redis_client()
    payloads = [
        JobEnvelope(
            type=str(jt),
            payload=payload,
            max_attempts=settings.job_max_retries,
        ).to_json()
        for jt, payload in jobs
    ]
    length = client.rpush(_queue_key(settings), *payloads)
    logger.info("jobs_enqueued", count=len(jobs), queue_length=length)
    return int(length)


def dequeue_job(
    *,
    settings: Settings | None = None,
    client: redis.Redis | None = None,
    block_seconds: int | None = None,
) -> JobEnvelope | None:
    """Pop the next job (checks legacy inspection queue first)."""
    settings = settings or get_settings()
    client = client or get_redis_client()
    block = block_seconds if block_seconds is not None else settings.worker_poll_seconds

    # Drain legacy inspection-only queue first (non-blocking)
    legacy_raw = client.lpop(_legacy_inspection_key(settings))
    if legacy_raw:
        return JobEnvelope.from_raw(legacy_raw)

    try:
        result = client.blpop(_queue_key(settings), timeout=block)
    except redis.TimeoutError:
        return None
    if not result:
        return None
    _, raw = result
    return JobEnvelope.from_raw(raw)


def requeue_job(
    envelope: JobEnvelope,
    *,
    settings: Settings | None = None,
    client: redis.Redis | None = None,
) -> int:
    """Re-enqueue a failed job for retry."""
    settings = settings or get_settings()
    client = client or get_redis_client()
    retry = JobEnvelope(
        type=envelope.type,
        payload=envelope.payload,
        attempt=envelope.attempt + 1,
        max_attempts=envelope.max_attempts,
    )
    length = client.rpush(_queue_key(settings), retry.to_json())
    logger.info(
        "job_requeued",
        job_type=retry.type,
        attempt=retry.attempt,
        queue_length=length,
    )
    return int(length)


def get_queue_length(
    *,
    settings: Settings | None = None,
    client: redis.Redis | None = None,
) -> int:
    settings = settings or get_settings()
    client = client or get_redis_client()
    return int(client.llen(_queue_key(settings))) + int(
        client.llen(_legacy_inspection_key(settings))
    )


def get_queue_stats(
    *,
    settings: Settings | None = None,
    client: redis.Redis | None = None,
) -> dict[str, int]:
    settings = settings or get_settings()
    client = client or get_redis_client()
    unified = int(client.llen(_queue_key(settings)))
    legacy = int(client.llen(_legacy_inspection_key(settings)))
    return {
        "unified_queue": unified,
        "legacy_inspection_queue": legacy,
        "total": unified + legacy,
    }
