"""Artifact storage paths for inspection screenshots and HTML snapshots."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.core.config import Settings


def ensure_inspection_dirs(settings: Settings) -> None:
    settings.snapshots_dir.mkdir(parents=True, exist_ok=True)
    settings.screenshots_dir.mkdir(parents=True, exist_ok=True)


def artifact_paths(
    settings: Settings,
    lead_id: int,
    inspection_id: int,
) -> tuple[Path, Path]:
    """Return (screenshot_path, html_snapshot_path) for a new inspection."""
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    screenshot = settings.screenshots_dir / f"lead_{lead_id}_insp_{inspection_id}_{ts}.png"
    snapshot = settings.snapshots_dir / f"lead_{lead_id}_insp_{inspection_id}_{ts}.html"
    return screenshot, snapshot
