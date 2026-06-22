"""Scheduler process — enqueues due scheduled tasks."""

from __future__ import annotations

import signal
import sys
import time

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import get_session_factory
from app.scheduler.service import run_due_scheduled_tasks

logger = get_logger(__name__)
_running = True


def _handle_stop(signum, frame) -> None:
    global _running
    logger.info("scheduler_stopping", signal=signum)
    _running = False


def run_scheduler(*, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    configure_logging(settings)
    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    logger.info("scheduler_started", poll_seconds=settings.scheduler_poll_seconds)

    while _running:
        try:
            with get_session_factory(settings)() as db:
                tasks = run_due_scheduled_tasks(db)
                if tasks:
                    logger.info("scheduler_tick", tasks_run=len(tasks))
        except Exception:
            logger.exception("scheduler_tick_failed")
        time.sleep(settings.scheduler_poll_seconds)

    logger.info("scheduler_stopped")


def main() -> None:
    run_scheduler()
    sys.exit(0)


if __name__ == "__main__":
    main()
