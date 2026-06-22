"""Tests for export file path security."""

from pathlib import Path

import pytest

from app.models.export_job import ExportJob
from app.utils.file_storage import ExportFileError, export_filename, resolve_export_download_path


def test_export_filename_format() -> None:
    assert export_filename(42, "20260101_120000") == "leads_export_42_20260101_120000.csv"


def test_resolve_export_download_path(tmp_path: Path) -> None:
    file_path = tmp_path / export_filename(1, "test")
    file_path.write_text("lead_id\n1\n", encoding="utf-8")
    job = ExportJob(id=1, format="csv", status="completed", file_path=file_path.name)
    resolved = resolve_export_download_path(tmp_path, job)
    assert resolved.exists()


def test_reject_path_outside_export_dir(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.csv"
    outside.write_text("x", encoding="utf-8")
    job = ExportJob(id=1, format="csv", status="completed", file_path=str(outside))
    with pytest.raises(ExportFileError):
        resolve_export_download_path(tmp_path, job)
