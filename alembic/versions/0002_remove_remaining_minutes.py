"""remove remaining_minutes column - now computed dynamically

Revision ID: 0002
Revises: 0001
Create Date: 2025-03-21 00:01:00.000000

remaining_minutes is no longer stored in the DB.
It is computed on every API call as:
    remaining = estimated_minutes - minutes_elapsed_since_creation
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the stored column — value is now computed live
    op.drop_column("tasks", "remaining_minutes")


def downgrade() -> None:
    # Re-add the column if rolling back (will be NULL for existing rows)
    op.add_column(
        "tasks",
        sa.Column("remaining_minutes", sa.Integer(), nullable=True),
    )
