"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("github_id", sa.Integer(), nullable=False),
        sa.Column("github_username", sa.String(100), nullable=False),
        sa.Column("github_avatar_url", sa.String(500), nullable=True),
        sa.Column("github_name", sa.String(200), nullable=True),
        sa.Column("github_bio", sa.Text(), nullable=True),
        sa.Column("github_location", sa.String(200), nullable=True),
        sa.Column("github_blog", sa.String(500), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("public_repos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("followers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skill_json", sa.JSON(), nullable=True),
        sa.Column("skill_vector", Vector(128), nullable=True),
        sa.Column("skill_last_updated", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_github_id", "users", ["github_id"], unique=True)
    op.create_index("ix_users_github_username", "users", ["github_username"], unique=True)

    op.create_table(
        "repositories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("github_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(300), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_login", sa.String(100), nullable=False),
        sa.Column("html_url", sa.String(500), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("forks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("open_issues_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("primary_language", sa.String(100), nullable=True),
        sa.Column("topics", sa.JSON(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_indexed", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_repositories_id", "repositories", ["id"])
    op.create_index("ix_repositories_github_id", "repositories", ["github_id"], unique=True)
    op.create_index("ix_repositories_full_name", "repositories", ["full_name"], unique=True)
    op.create_index("ix_repositories_owner_login", "repositories", ["owner_login"])
    op.create_index("ix_repositories_stars", "repositories", ["stars"])

    op.create_table(
        "issues",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("github_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("html_url", sa.String(500), nullable=False),
        sa.Column("state", sa.String(20), nullable=False, server_default="open"),
        sa.Column("labels", sa.JSON(), nullable=True),
        sa.Column("is_good_first_issue", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_help_wanted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("required_skills", sa.JSON(), nullable=True),
        sa.Column("skill_vector", Vector(128), nullable=True),
        sa.Column("complexity_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("comments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("author_login", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_issues_id", "issues", ["id"])
    op.create_index("ix_issues_github_id", "issues", ["github_id"], unique=True)
    op.create_index("ix_issues_state", "issues", ["state"])
    op.create_index("ix_issues_is_good_first_issue", "issues", ["is_good_first_issue"])
    op.create_index("ix_issues_is_help_wanted", "issues", ["is_help_wanted"])
    op.create_index("ix_issues_repository_id", "issues", ["repository_id"])

    op.create_table(
        "saved_issues",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("issue_id", sa.Integer(), nullable=False),
        sa.Column("saved_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="saved"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_saved_issues_id", "saved_issues", ["id"])
    op.create_index("ix_saved_issues_user_id", "saved_issues", ["user_id"])
    op.create_index("ix_saved_issues_issue_id", "saved_issues", ["issue_id"])


def downgrade() -> None:
    op.drop_table("saved_issues")
    op.drop_table("issues")
    op.drop_table("repositories")
    op.drop_table("users")
