"""Add scheduled_tasks table.

Revision ID: 006_scheduled_tasks
Revises: 005_export_row_count
Create Date: 2026-06-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_scheduled_tasks"
down_revision: Union[str, None] = "005_export_row_count"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scheduled_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("task_type", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("interval_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(length=50), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scheduled_tasks_task_type"), "scheduled_tasks", ["task_type"])
    op.create_index(op.f("ix_scheduled_tasks_enabled"), "scheduled_tasks", ["enabled"])


def downgrade() -> None:
    op.drop_index(op.f("ix_scheduled_tasks_enabled"), table_name="scheduled_tasks")
    op.drop_index(op.f("ix_scheduled_tasks_task_type"), table_name="scheduled_tasks")
    op.drop_table("scheduled_tasks")
