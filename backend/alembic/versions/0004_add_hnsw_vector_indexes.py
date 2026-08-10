"""Add HNSW vector indexes for fast approximate nearest-neighbor search

Creates HNSW (Hierarchical Navigable Small World) indexes on the
skill_vector columns of issues and users tables.

Benefits:
  - Reduces vector search from O(n) full scan to O(log n)
  - Target: ~5ms per query (vs ~400ms+ for exact NN at 100K issues)
  - Maintains >95% recall at ef=100

The index automatically accelerates queries like:
  SELECT ... FROM issues WHERE state='open'
  ORDER BY skill_vector <=> :user_vec LIMIT 300

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-10

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # HNSW index on issues.skill_vector (partial: only open issues)
    # m=16: max connections per layer (good balance speed/recall)
    # ef_construction=200: high-quality index for read-heavy workload
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_issues_skill_vector_hnsw "
        "ON issues USING hnsw (skill_vector vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 200) "
        "WHERE state = 'open'"
    )

    # HNSW index on users.skill_vector (all users — skill lookup is read-heavy)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_users_skill_vector_hnsw "
        "ON users USING hnsw (skill_vector vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 200)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_issues_skill_vector_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_users_skill_vector_hnsw")
