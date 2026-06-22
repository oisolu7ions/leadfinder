"""Add row_count to export_jobs.

Revision ID: 005_export_row_count
Revises: 004_outreach_draft_fields
Create Date: 2026-06-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_export_row_count"
down_revision: Union[str, None] = "004_outreach_draft_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("export_jobs", sa.Column("row_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("export_jobs", "row_count")
