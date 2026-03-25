"""initial schema - create users and tasks tables

Revision ID: 0001
Revises:
Create Date: 2025-03-21 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the initial users and tasks tables."""

    # Enable the uuid-ossp extension (needed for uuid_generate_v4 in raw SQL;
    # SQLAlchemy uses Python-side uuid.uuid4() so this is just good practice)
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(225), nullable=False),
        sa.Column("passwordhash", sa.String(255), nullable=False),
    )
    op.create_index("idx_users_name", "users", ["name"], unique=True)

    # ── tasks ──────────────────────────────────────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(225), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("priority", sa.String(10), nullable=False, server_default="P3"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("remaining_minutes", sa.Integer(), nullable=True),
        sa.Column("is_done", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_index("idx_tasks_created_by", "tasks", ["created_by_id"])


def downgrade() -> None:
    """Drop the tasks and users tables (in reverse dependency order)."""
    op.drop_index("idx_tasks_created_by", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("idx_users_name", table_name="users")
    op.drop_table("users")
