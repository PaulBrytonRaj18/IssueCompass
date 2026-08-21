"""Regression coverage for PgBouncer-safe asyncpg engine configuration."""

from app.core.config import Settings
from app.core.database import PGCONN_ARGS, _prepared_statement_name


def test_prepared_statement_caches_are_disabled_for_pgbouncer() -> None:
    """Disable both the driver and SQLAlchemy dialect statement caches."""
    assert PGCONN_ARGS["statement_cache_size"] == 0
    assert PGCONN_ARGS["prepared_statement_cache_size"] == 0


def test_prepared_statement_names_are_unique() -> None:
    """Prevent PgBouncer backends from receiving colliding asyncpg names."""
    names = {_prepared_statement_name() for _ in range(100)}

    assert len(names) == 100
    assert all(name.startswith("__issuecompass_") and name.endswith("__") for name in names)
    assert PGCONN_ARGS["prepared_statement_name_func"] is _prepared_statement_name


def test_null_pool_is_the_safe_default() -> None:
    """Keep deployments safe when DATABASE_URL points to transaction PgBouncer."""
    assert Settings.model_fields["DB_POOL_SIZE"].default == 0
