"""Shared enumerations used across models and services."""

from enum import StrEnum


class ScanJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LeadStatus(StrEnum):
    NEW = "new"
    REVIEWED = "reviewed"
    QUALIFIED = "qualified"
    DISQUALIFIED = "disqualified"
    CONTACTED = "contacted"
    ARCHIVED = "archived"


class ExportJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class OutreachDraftStatus(StrEnum):
    DRAFT_READY = "draft_ready"
    REVIEWED = "reviewed"
    ARCHIVED = "archived"

    # Legacy values (may exist in older rows before migration)
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"


ACTIVE_DRAFT_STATUSES = frozenset(
    {OutreachDraftStatus.DRAFT_READY.value, OutreachDraftStatus.DRAFT.value}
)

REVIEWED_DRAFT_STATUSES = frozenset(
    {OutreachDraftStatus.REVIEWED.value, OutreachDraftStatus.APPROVED.value}
)


class ExportFormat(StrEnum):
    CSV = "csv"
