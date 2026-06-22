"""Add reachability_score, ssl_score, breakdown JSON to lead_scores.

Revision ID: 003_scoring_fields
Revises: 002_address_dedup
Create Date: 2026-06-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_scoring_fields"
down_revision: Union[str, None] = "002_address_dedup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lead_scores",
        sa.Column("reachability_score", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "lead_scores",
        sa.Column("ssl_score", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("lead_scores", sa.Column("breakdown", sa.JSON(), nullable=True))
    op.alter_column("lead_scores", "reachability_score", server_default=None)
    op.alter_column("lead_scores", "ssl_score", server_default=None)


def downgrade() -> None:
    op.drop_column("lead_scores", "breakdown")
    op.drop_column("lead_scores", "ssl_score")
    op.drop_column("lead_scores", "reachability_score")
