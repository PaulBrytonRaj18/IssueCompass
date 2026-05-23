"""
Database connection architecture.

PgBouncer Transaction Pooling Notes:
  asyncpg uses prepared statements internally. PgBouncer transaction-mode
  pooling routes each transaction to a different backend connection, which
  causes prepared statement conflicts (InvalidSQLStatementNameError and
  DuplicatePreparedStatementError).

  Fix: set BOTH statement_cache_size=0 AND prepared_statement_cache_size=0
  in connect_args.  asyncpg 0.29.0 deprecated the former in favour of the
  latter; setting both guarantees the cache is disabled across all versions.
"""

import logging

import asyncpg
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

DATABASE_URL = settings.DATABASE_URL
if "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# ── PgBouncer-safe connection arguments ────────────────────────────────
# Both statement_cache_size and prepared_statement_cache_size are set to
# 0 to cover both old (<0.28) and new (>=0.28) asyncpg parameter names.
# Without this, PgBouncer transaction pooling causes:
#   InvalidSQLStatementNameError — prepared stmt does not exist on backend
#   DuplicatePreparedStatementError — same stmt name reused across backends
PGCONN_ARGS: dict = {
    "timeout": 10,
    "statement_cache_size": 0,
    "prepared_statement_cache_size": 0,
    "command_timeout": 30,
}

# Log connection target with credentials masked
def _mask_db_url(raw: str) -> str:
    if "@" in raw:
        return raw.split("@")[0].split("://")[0] + "://****@" + raw.split("@", 1)[1]
    return raw
asyncpg_version = getattr(asyncpg, "__version__", "unknown")
logger.info(
    "DB_ENGINE: creating async engine — target=%s asyncpg=%s "
    "pool=3/2 recycle=300s stmt_cache=0 prep_stmt_cache=0 "
    "pre_ping=True LIFO=True isolation=READ_COMMITTED",
    _mask_db_url(settings.DATABASE_URL),
    asyncpg_version,
)

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_use_lifo=True,
    pool_size=3,
    max_overflow=2,
    pool_recycle=300,
    pool_timeout=5,
    connect_args=PGCONN_ARGS,
    isolation_level="READ_COMMITTED",
)

# ── Pool diagnostics logging ──────────────────────────────────────
@event.listens_for(engine.sync_engine, "connect")
def _on_db_connect(dbapi_connection, connection_record):
    logger.debug("DB connection established")


@event.listens_for(engine.sync_engine, "checkin")
def _on_db_checkin(dbapi_connection, connection_record):
    logger.debug("DB connection returned to pool")


@event.listens_for(engine.sync_engine, "checkout")
def _on_db_checkout(dbapi_connection, connection_record, connection_proxy):
    logger.debug("DB connection checked out from pool")


AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def close_db():
    """Dispose of the application engine pool on shutdown.

    Releases all pooled connections so the process exits cleanly and
    PgBouncer can immediately reclaim the backend connections.
    """
    if engine is not None:
        try:
            pool = engine.pool
            logger.info(
                "DB_DISPOSE: closing pool — size=%d checked_in=%d checked_out=%d overflow=%d",
                getattr(pool, "size", lambda: -1)(),
                getattr(pool, "checkedin", lambda: -1)(),
                getattr(pool, "checkedout", lambda: -1)(),
                getattr(pool, "overflow", lambda: -1)(),
            )
        except Exception:
            pass
        await engine.dispose()
        logger.info("DB_DISPOSE: engine pool disposed")


async def get_pool_status() -> dict:
    """Return pool statistics for health / metrics endpoints."""
    try:
        pool = engine.pool
        return {
            "size": getattr(pool, "size", lambda: 0)(),
            "checked_in": getattr(pool, "checkedin", lambda: 0)(),
            "checked_out": getattr(pool, "checkedout", lambda: 0)(),
            "overflow": getattr(pool, "overflow", lambda: 0)(),
        }
    except Exception:
        return {"error": "pool not available"}


async def init_db():
    """Ensure DB extensions exist. Tables managed by Alembic migrations.

    Uses a short-lived engine with NullPool so the startup connection does
    NOT pollute the application pool's prepared-statement state.  This
    avoids the risk of a ``CREATE EXTENSION`` prepared statement lingering
    across PgBouncer backend switches.

    All connections from this function set statement_cache_size=0 and
    prepared_statement_cache_size=0 so that asyncpg does NOT cache prepared
    statements across PgBouncer backend connections.  Without this,
    PgBouncer transaction pooling causes:
      - InvalidSQLStatementNameError
      - DuplicatePreparedStatementError
    """
    from sqlalchemy.pool import NullPool

    try:
        asyncpg_version = getattr(asyncpg, "__version__", "unknown")
        logger.info(
            "DB_INIT: creating short-lived engine — asyncpg=%s "
            "NullPool stmt_cache=0 prep_stmt_cache=0",
            asyncpg_version,
        )
        tmp_engine = create_async_engine(
            DATABASE_URL,
            poolclass=NullPool,
            connect_args={
                "timeout": 10,
                "statement_cache_size": 0,
                "prepared_statement_cache_size": 0,
                "command_timeout": 30,
            },
        )
        async with tmp_engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await tmp_engine.dispose()
        logger.info(
            "DB_INIT: database extension verified — "
            "PgBouncer-safe config active (stmt_cache=0)",
        )
    except Exception as e:
        logger.warning("DB_INIT: could not create vector extension (managed PG?): %s", e)
