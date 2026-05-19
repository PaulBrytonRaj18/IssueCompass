"""Add missing saved_searches table and fix partial index for state + skill_vector

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "saved_searches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("query", sa.String(500), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("notify", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_saved_searches_id", "saved_searches", ["id"])
    op.create_index("ix_saved_searches_user_id", "saved_searches", ["user_id"])

    op.drop_index("ix_issues_state_vector", table_name="issues")
    op.create_index(
        "ix_issues_state_vector",
        "issues",
        ["state", "skill_vector"],
        postgresql_where=sa.text("skill_vector IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_issues_state_vector", table_name="issues")
    op.create_index(
        "ix_issues_state_vector",
        "issues",
        ["state"],
        postgresql_where=sa.text("skill_vector IS NOT NULL"),
    )
    op.drop_table("saved_searches")
