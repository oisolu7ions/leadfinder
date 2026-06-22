"""Backward-compatible inspection queue — delegates to unified job queue."""

from __future__ import annotations

import redis

from app.core.config import Settings, get_settings
from app.workers.enqueue import enqueue_inspection as _enqueue_inspection
from app.workers.enqueue import enqueue_inspections as _enqueue_inspections
from app.workers.queue import get_queue_length as _get_queue_length


def enqueue_inspection(
    lead_id: int,
    *,
    auto_score: bool = True,
    settings: Settings | None = None,
    client: redis.Redis | None = None,
) -> int:
    """Push an inspection job onto the unified queue."""
    return _enqueue_inspection(lead_id, auto_score=auto_score, settings=settings)


def enqueue_inspections(
    lead_ids: list[int],
    *,
    auto_score: bool = True,
    settings: Settings | None = None,
    client: redis.Redis | None = None,
) -> int:
    """Queue multiple lead inspections."""
    return _enqueue_inspections(lead_ids, auto_score=auto_score, settings=settings)


def get_queue_length(
    *,
    settings: Settings | None = None,
    client: redis.Redis | None = None,
) -> int:
    return _get_queue_length(settings=settings, client=client)
