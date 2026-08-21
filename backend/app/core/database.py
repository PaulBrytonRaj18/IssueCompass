"""
Database connection architecture.

Connection Pooling Strategy:
  When DB_POOL_SIZE > 0: QueuePool (use with direct PostgreSQL or PgBouncer
  session pooling). When DB_POOL_SIZE = 0: NullPool (the safe default for
  PgBouncer transaction/statement pooling).

  statement_cache_size=0 disables asyncpg's cache; SQLAlchemy's dialect cache
  is separately disabled with prepared_statement_cache_size=0. A UUID-based
  statement-name function prevents name collisions on a reused backend.
"""

import logging
import socket
from uuid import uuid4

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

DATABASE_URL = settings.DATABASE_URL
if "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# ── Connection arguments (PgBouncer-safe) ─────────────────────────────
# asyncpg consumes statement_cache_size. prepared_statement_cache_size and
# prepared_statement_name_func are consumed by SQLAlchemy's asyncpg dialect
# before it calls asyncpg.connect(). Both caches must be off for PgBouncer
# transaction/statement pooling. The dialect still prepares statements, so
# UUID-derived names avoid collisions with asyncpg's process-local counter.
def _prepared_statement_name() -> str:
    return f"__issuecompass_{uuid4().hex}__"


PGCONN_ARGS: dict = {
    "timeout": 10,
    "statement_cache_size": 0,
    "prepared_statement_cache_size": 0,
    "prepared_statement_name_func": _prepared_statement_name,
    "command_timeout": 30,
    "ssl": settings.DB_SSL_MODE,
}

# ── Pool class selection ──────────────────────────────────────────────
# DB_POOL_SIZE > 0  → AsyncAdaptedQueuePool  (connection reuse, lower latency)
# DB_POOL_SIZE = 0  → NullPool               (PgBouncer transaction/statement safe)
#
# SQLAlchemy's create_async_engine auto-selects AsyncAdaptedQueuePool
# (the async-safe equivalent of QueuePool) when pool_size is provided.
_pool_size = settings.DB_POOL_SIZE
_use_queue = _pool_size > 0

if _use_queue:
    _poolclass = None  # auto: AsyncAdaptedQueuePool via pool_size kwarg
    _pool_kwargs = {
        "pool_size": _pool_size,
        "max_overflow": settings.DB_POOL_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    _pool_label = f"AsyncAdaptedQueuePool(size={_pool_size}, overflow={settings.DB_POOL_OVERFLOW})"
else:
    _poolclass = NullPool
    _pool_kwargs = {"pool_pre_ping": True}
    _pool_label = "NullPool"

# ── DNS diagnostics at startup ───────────────────────────
_db_host = (
    settings.DATABASE_URL.split("@")[-1].split(":")[0]
    if "@" in settings.DATABASE_URL
    else "unknown"
)
try:
    _addrs = socket.getaddrinfo(
        _db_host,
        5432,
        socket.AF_UNSPEC,
        socket.SOCK_STREAM,
    )
    _has_ipv4 = any(a[0] == socket.AF_INET for a in _addrs)
    _has_ipv6 = any(a[0] == socket.AF_INET6 for a in _addrs)
    logger.info(
        "DB_DNS: %s → %d address(es) [v4=%s v6=%s]",
        _db_host,
        len(_addrs),
        _has_ipv4,
        _has_ipv6,
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
    "DB_ENGINE: creating async engine — target=%s asyncpg=%s poolclass=%s "
    "asyncpg_stmt_cache=0 dialect_stmt_cache=0 unique_stmt_names=true",
    _mask_db_url(settings.DATABASE_URL),
    asyncpg_version,
    _pool_label,
)

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=_poolclass,
    connect_args=PGCONN_ARGS,
    isolation_level="READ_COMMITTED",
    **_pool_kwargs,
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


async def _enter_session(session):
    """Open session connection — extracted so tenacity can retry it."""
    await session.__aenter__()


_enter_session = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)(_enter_session)


async def get_db():
    session = AsyncSessionLocal()
    try:
        await _enter_session(session)
    except Exception:
        await session.__aexit__(None, None, None)
        raise
    try:
        yield session
    finally:
        await session.close()


async def close_db():
    """Dispose of engine on shutdown — releases all connections."""
    if engine is not None:
        logger.info("DB_DISPOSE: disposing engine (%s)", _pool_label)
        await engine.dispose()


async def get_pool_status() -> dict:
    """Return pool status for health / metrics endpoints."""
    pool = engine.pool
    poolclass = type(pool).__name__
    if "Pool" in poolclass and poolclass != "NullPool":
        return {
            "poolclass": poolclass,
            "size": pool.size(),  # type: ignore[attr-defined]
            "checked_in": pool.checkedin(),  # type: ignore[attr-defined]
            "checked_out": pool.checkedout(),  # type: ignore[attr-defined]
            "overflow": pool.overflow(),  # type: ignore[attr-defined]
            "status": "pooled",
        }
    return {"poolclass": "NullPool", "status": "no-pool"}
