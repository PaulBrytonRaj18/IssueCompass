import asyncio
import os
from logging.config import fileConfig

from alembic import context
from app.core.database import Base
from app.models.models import *  # noqa: F401, F403
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

# ── Load database URL from environment ─────────────────────────
# Never rely on ConfigParser %(...)s interpolation in alembic.ini;
# Python's ConfigParser treats that as option references, not env vars.
_database_url = os.environ.get("DATABASE_URL_DIRECT") or os.environ.get("DATABASE_URL", "")
if not _database_url:
    from app.core.config import get_settings

    _database_url = get_settings().DATABASE_URL

# DATABASE_URL_DIRECT bypasses PgBouncer for migration safety.
# When using PgBouncer transaction pooling, asyncpg prepared statements
# conflict because the backend connection changes between transactions.
_migration_url = _database_url
if "+asyncpg" not in _database_url:
    _database_url = _database_url.replace("postgresql://", "postgresql+asyncpg://")
    _migration_url = _database_url

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


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    config_section = dict(config.get_section(config.config_ini_section))
    config_section["sqlalchemy.url"] = _migration_url
    # statement_cache_size=0 is REQUIRED when connecting via PgBouncer
    # transaction pooling. Without it, asyncpg prepared statements
    # conflict because PgBouncer routes subsequent queries to different
    # backend connections, causing DuplicatePreparedStatementError.
    connectable = async_engine_from_config(
        config_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={
            "statement_cache_size": 0,
            "timeout": 10,
            "command_timeout": 60,
        },
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
