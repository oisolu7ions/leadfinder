"""Unified background worker — processes Redis job queue."""

from __future__ import annotations

import signal
import sys
import time

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import get_session_factory
from app.workers.jobs.handlers import handle_job
from app.workers.queue import dequeue_job, get_queue_stats, requeue_job

logger = get_logger(__name__)
_running = True


def _handle_stop(signum, frame) -> None:
    global _running
    logger.info("worker_stopping", signal=signum)
    _running = False


def run_worker(*, settings: Settings | None = None) -> None:
    """Process jobs from the unified queue one at a time (conservative default)."""
    settings = settings or get_settings()
    configure_logging(settings)
    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    logger.info(
        "worker_started",
        queue=settings.job_queue_name,
        max_retries=settings.job_max_retries,
        poll_seconds=settings.worker_poll_seconds,
        browser_enabled=settings.inspection_browser_enabled,
    )

    while _running:
        envelope = dequeue_job(settings=settings)
        if envelope is None:
            continue

        logger.info(
            "worker_processing",
            job_type=envelope.type,
            attempt=envelope.attempt,
            payload=envelope.payload,
        )
        try:
            with get_session_factory(settings)() as db:
                handle_job(db, envelope)
        except Exception as exc:
            logger.exception(
                "worker_job_failed",
                job_type=envelope.type,
                attempt=envelope.attempt,
                error=str(exc),
            )
            if envelope.attempt < envelope.max_attempts:
                requeue_job(envelope, settings=settings)
                time.sleep(settings.job_retry_delay_seconds)
            else:
                logger.error(
                    "worker_job_exhausted_retries",
                    job_type=envelope.type,
                    payload=envelope.payload,
                )

    logger.info("worker_stopped", stats=get_queue_stats(settings=settings))


def main() -> None:
    run_worker()
    sys.exit(0)


if __name__ == "__main__":
    main()
