"""Route tests — requires running DB, skip if no DB available."""
import pytest


@pytest.mark.skip(reason="Requires running PostgreSQL with pgvector")
def test_health_with_db():
    pass


@pytest.mark.skip(reason="Requires running PostgreSQL with pgvector")
def test_stats_with_db():
    pass
