"""
Database connection architecture — Supabase Session Pooler.

PgBouncer Session Pooling Notes:
  asyncpg uses prepared statements internally. PgBouncer session-mode
  pooling routes each transaction to a different backend connection, which
  causes prepared statement conflicts (InvalidSQLStatementNameError and
  DuplicatePreparedStatementError).

  Fix: set BOTH statement_cache_size=0 AND prepared_statement_cache_size=0
  in connect_args.  asyncpg 0.29.0 deprecated the former in favour of the
  latter; setting both guarantees the cache is disabled across all versions.

  poolclass=NullPool ensures every connection is short-lived, compatible
  with PgBouncer session pooling.
"""

import logging
import socket

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

DATABASE_URL = settings.DATABASE_URL
if "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# ── PgBouncer-safe connection arguments ────────────────────────────────
# Both statement_cache_size and prepared_statement_cache_size are set to
# 0 to cover both old (<0.28) and new (>=0.28) asyncpg parameter names.
# Without this, PgBouncer session pooling causes:
#   InvalidSQLStatementNameError — prepared stmt does not exist on backend
#   DuplicatePreparedStatementError — same stmt name reused across backends
PGCONN_ARGS: dict = {
    "timeout": 10,
    "statement_cache_size": 0,
    "prepared_statement_cache_size": 0,
    "command_timeout": 30,
    "ssl": "require",
}

# ── DNS diagnostics at startup ───────────────────────────
_db_host = (
    settings.DATABASE_URL.split("@")[-1].split(":")[0]
    if "@" in settings.DATABASE_URL else "unknown"
)
try:
    _addrs = socket.getaddrinfo(
        _db_host, 5432, socket.AF_UNSPEC, socket.SOCK_STREAM,
    )
    _has_ipv4 = any(a[0] == socket.AF_INET for a in _addrs)
    _has_ipv6 = any(a[0] == socket.AF_INET6 for a in _addrs)
    logger.info(
        "DB_DNS: %s → %d address(es) [v4=%s v6=%s]",
        _db_host, len(_addrs), _has_ipv4, _has_ipv6,
    )
    for a in _addrs:
        family = "IPv6" if a[0] == socket.AF_INET6 else "IPv4"
        logger.info("DB_DNS:   %s %s", family, a[4][0])
    if not _has_ipv4:
        logger.warning(
            "DB_DNS: %s has no IPv4 A record — fails on IPv4-only networks",
            _db_host,
        )
    if not _has_ipv6:
        logger.warning(
            "DB_DNS: %s has no IPv6 AAAA record — fails on IPv6-only networks",
            _db_host,
        )
except Exception as _dns_err:
    logger.warning("DB_DNS: could not resolve %s: %s", _db_host, _dns_err)

# Log connection target with credentials masked
def _mask_db_url(raw: str) -> str:
    cleaned = raw.replace("+asyncpg", "")
    if "@" in cleaned:
        return cleaned.split("@")[0].split("://")[0] + "://****@" + cleaned.split("@", 1)[1]
    return cleaned

asyncpg_version = getattr(asyncpg, "__version__", "unknown")
logger.info(
    "DB_ENGINE: creating async engine — target=%s asyncpg=%s "
    "poolclass=NullPool stmt_cache=0 prep_stmt_cache=0 pre_ping=True",
    _mask_db_url(settings.DATABASE_URL),
    asyncpg_version,
)

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=NullPool,
    pool_pre_ping=True,
    connect_args=PGCONN_ARGS,
    isolation_level="READ_COMMITTED",
)

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
    """Dispose of engine on shutdown — releases all connections to PgBouncer."""
    if engine is not None:
        logger.info("DB_DISPOSE: disposing engine (NullPool)")
        await engine.dispose()


async def get_pool_status() -> dict:
    """Return pool status for health / metrics endpoints (NullPool = no pooling)."""
    return {"poolclass": "NullPool", "status": "no-pool"}
