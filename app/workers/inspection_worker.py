"""Background inspection worker — delegates to unified worker."""

from __future__ import annotations

import sys

from app.workers.worker import main as run_unified_worker
from app.workers.worker import run_worker


def run_inspection_worker(*, poll_seconds: int = 5) -> None:
    """Legacy entrypoint; runs the unified job worker."""
    run_worker()


def main() -> None:
    run_unified_worker()


if __name__ == "__main__":
    main()
    sys.exit(0)
