"""
Alembic environment — synchronous psycopg2 engine for migration stability.

WHY SYNC:
  asyncpg (used by the FastAPI runtime) has prepared-statement caching that
  conflicts with PgBouncer session pooling, causing
  DuplicatePreparedStatementError.  While we can disable the cache with
  statement_cache_size=0, Alembic's async support adds unnecessary
  complexity.  A synchronous psycopg2 engine avoids these issues entirely
  and is the recommended approach for Alembic with PgBouncer.
"""

import os
from logging.config import fileConfig

from alembic import context
from app.core.database import Base
from app.models.models import *  # noqa: F401, F403
from sqlalchemy import create_engine, pool

config = context.config

# ── Load database URL from environment ─────────────────────────
_database_url = os.environ.get("DATABASE_URL", "")
if not _database_url:
    from app.core.config import get_settings
    _database_url = get_settings().DATABASE_URL

# Strip async driver prefix — Alembic uses sync psycopg2 engine
_migration_url = _database_url.replace("+asyncpg", "")

# SSL mode — production (Supabase) requires SSL; CI/localhost does not.
# Set DB_SSL_MODE=disable for local/GitHub Actions PostgreSQL without SSL.
_ssl_mode = os.environ.get("DB_SSL_MODE", "")
if not _ssl_mode:
    from app.core.config import get_settings
    _ssl_mode = get_settings().DB_SSL_MODE

config.set_main_option("sqlalchemy.url", _migration_url)

# ── Logging configuration ─────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = create_engine(
        _migration_url,
        poolclass=pool.NullPool,
        connect_args={
            "connect_timeout": 10,
            "sslmode": _ssl_mode,
        },
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
