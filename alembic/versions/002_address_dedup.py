"""Add normalized_address_key for address-based deduplication.

Revision ID: 002_address_dedup
Revises: 001_initial
Create Date: 2026-06-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_address_dedup"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "business_leads",
        sa.Column("normalized_address_key", sa.String(length=500), nullable=True),
    )
    op.create_index("ix_leads_dedup_address", "business_leads", ["normalized_address_key"])


def downgrade() -> None:
    op.drop_index("ix_leads_dedup_address", table_name="business_leads")
    op.drop_column("business_leads", "normalized_address_key")
