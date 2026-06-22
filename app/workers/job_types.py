"""Background job type constants."""

from enum import StrEnum


class JobType(StrEnum):
    SCAN = "scan"
    INSPECT = "inspect"
    INSPECT_BULK = "inspect_bulk"
    SCORE = "score"
    SCORE_BULK = "score_bulk"
    OUTREACH = "outreach"
    EXPORT = "export"


class ScheduledTaskType(StrEnum):
    SCAN = "scan"
    INSPECT_UNREVIEWED = "inspect_unreviewed"
    SCORE_UNSCORED = "score_unscored"
    EXPORT = "export"
