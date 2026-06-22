"""Add primary_angle and context JSON to outreach_drafts; normalize statuses.

Revision ID: 004_outreach_draft_fields
Revises: 003_scoring_fields
Create Date: 2026-06-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_outreach_draft_fields"
down_revision: Union[str, None] = "003_scoring_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "outreach_drafts",
        sa.Column("primary_angle", sa.String(length=80), nullable=True),
    )
    op.add_column("outreach_drafts", sa.Column("context", sa.JSON(), nullable=True))

    op.execute(
        sa.text(
            "UPDATE outreach_drafts SET status = 'draft_ready' WHERE status = 'draft'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE outreach_drafts SET status = 'reviewed' WHERE status = 'approved'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE outreach_drafts SET status = 'archived' WHERE status IN ('rejected', 'sent')"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE outreach_drafts SET status = 'draft' WHERE status = 'draft_ready'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE outreach_drafts SET status = 'approved' WHERE status = 'reviewed'"
        )
    )
    op.drop_column("outreach_drafts", "context")
    op.drop_column("outreach_drafts", "primary_angle")
