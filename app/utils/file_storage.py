"""Safe file path helpers for export downloads."""

from __future__ import annotations

from pathlib import Path

from app.models.export_job import ExportJob


class ExportFileError(Exception):
    """Export file cannot be accessed."""


def export_filename(job_id: int, timestamp: str) -> str:
    return f"leads_export_{job_id}_{timestamp}.csv"


def resolve_export_download_path(export_dir: Path, job: ExportJob) -> Path:
    """Return a validated path for downloading an export file."""
    if not job.file_path:
        raise ExportFileError("Export file path not set")

    export_root = export_dir.resolve()
    candidate = Path(job.file_path)

    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        # Stored as filename or relative path under export_dir
        resolved = (export_root / candidate).resolve()

    try:
        resolved.relative_to(export_root)
    except ValueError as exc:
        raise ExportFileError("Export file path is outside the export directory") from exc

    if not resolved.exists():
        raise ExportFileError("Export file no longer exists on disk")

    if not resolved.is_file():
        raise ExportFileError("Export path is not a file")

    return resolved
