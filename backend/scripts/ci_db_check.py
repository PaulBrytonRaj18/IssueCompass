"""
CI database validation script — invoked by .github/workflows/ci.yml.

Usage:
    python -m scripts.ci_db_check CHECK_NAME

Checks:
    dns         — DNS resolution for database host
    tcp         — TCP connectivity to database host
    auth        — PostgreSQL authentication via asyncpg
    pgbouncer   — PgBouncer compatibility (statement cache, pool class)
    schema      — Schema introspection (expected tables)
    runtime     — Runtime asyncpg connectivity (SELECT 1)
"""

import asyncio
import os
import socket
import sys
from urllib.parse import urlparse


def _db_url() -> str:
    return os.environ.get("DATABASE_URL", "")


def _parsed():
    url = _db_url()
    parsed = urlparse(url.replace("+asyncpg", ""))
    return parsed.hostname or "unknown", parsed.port or 5432


def _ok(label: str, detail: str = "") -> None:
    msg = f"[PASS] {label}"
    if detail:
        msg += f" -- {detail}"
    print(msg)


def _fail(label: str, detail: str = "") -> None:
    msg = f"[FAIL] {label}"
    if detail:
        msg += f" -- {detail}"
    print(msg, file=sys.stderr)


def check_dns() -> int:
    host, port = _parsed()
    print(f"  Host: {host}")
    try:
        addrs = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        has_v4 = any(a[0] == socket.AF_INET for a in addrs)
        has_v6 = any(a[0] == socket.AF_INET6 for a in addrs)
        print(f"  DNS: {len(addrs)} address(es) [IPv4={has_v4} IPv6={has_v6}]")
        for a in addrs:
            family = "IPv6" if a[0] == socket.AF_INET6 else "IPv4"
            print(f"        {family}: {a[4][0]}")
        if not has_v4:
            print("  WARN: No IPv4 A record — will fail on IPv4-only networks")
        _ok("dns", f"{host} resolves")
        return 0
    except socket.gaierror as e:
        _fail("dns", f"cannot resolve {host}: {e}")
        return 1


def check_tcp() -> int:
    host, port = _parsed()
    connected = False
    for family, label in [(socket.AF_INET, "IPv4"), (socket.AF_INET6, "IPv6")]:
        try:
            addrs = socket.getaddrinfo(host, port, family, socket.SOCK_STREAM)
        except socket.gaierror:
            continue
        for addr in addrs:
            s = socket.socket(family, socket.SOCK_STREAM)
            s.settimeout(5)
            try:
                s.connect(addr[4])
                print(f"  TCP: {label} connected to {addr[4]}")
                connected = True
                s.close()
                break
            except OSError as e:
                print(f"  TCP: {label} {addr[4][0]} — {e}")
                s.close()
        if connected:
            break
    if not connected:
        _fail("tcp", f"could not connect to {host}:{port}")
        return 1
    _ok("tcp", f"{host}:{port} reachable")
    return 0


async def check_auth() -> int:
    import asyncpg

    url = _db_url()
    ssl_mode = os.environ.get("DB_SSL_MODE", "require")
    try:
        conn = await asyncpg.connect(url, statement_cache_size=0, timeout=10, ssl=ssl_mode)
        ver = await conn.fetchval("SELECT version()")
        print(f"  Connected: {ver}")
        await conn.close()
        _ok("auth", "PostgreSQL authentication succeeded")
        return 0
    except Exception as e:
        _fail("auth", str(e))
        return 1


def check_pgbouncer() -> int:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from app.core.database import PGCONN_ARGS, engine
    from sqlalchemy.pool import NullPool, QueuePool

    errors = 0

    stmt = PGCONN_ARGS.get("statement_cache_size")
    if stmt != 0:
        _fail("pgbouncer", f"statement_cache_size={stmt}, expected 0")
        errors += 1
    else:
        _ok("pgbouncer", "statement_cache_size=0")

    if PGCONN_ARGS.get("prepared_statement_cache_size") != 0:
        _fail("pgbouncer", "SQLAlchemy prepared_statement_cache_size is not 0")
        errors += 1
    else:
        _ok("pgbouncer", "SQLAlchemy prepared_statement_cache_size=0")

    if not callable(PGCONN_ARGS.get("prepared_statement_name_func")):
        _fail("pgbouncer", "prepared_statement_name_func is not configured")
        errors += 1
    else:
        _ok("pgbouncer", "unique prepared_statement_name_func configured")

    pool = engine.pool
    if isinstance(pool, NullPool):
        _ok("pgbouncer", "poolclass=NullPool (transaction/statement-mode PgBouncer safe)")
    elif isinstance(pool, QueuePool):
        _ok(
            "pgbouncer",
            f"poolclass=QueuePool(size={pool.size()}, overflow={pool._max_overflow}) (direct DB/session-mode PgBouncer)",
        )
    else:
        _fail("pgbouncer", f"unexpected poolclass={type(pool).__name__}")
        errors += 1

    return errors


_EXPECTED_HEAD = "0004"


async def check_schema() -> int:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from app.core.database import engine
    from sqlalchemy import text

    errors = 0
    try:
        async with engine.connect() as conn:
            # ── Check table existence ────────────────────────────────────
            r = await conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema='public' ORDER BY table_name"
                )
            )
            tables = {row[0] for row in r}
            print(f"  Tables ({len(tables)}): {sorted(tables)}")

            expected_tables = {
                "users",
                "repositories",
                "issues",
                "saved_searches",
                "saved_issues",
                "alembic_version",
            }
            missing = expected_tables - tables
            if missing:
                _fail("schema", f"missing tables: {sorted(missing)}")
                errors += 1
            else:
                _ok("schema", f"all {len(expected_tables)} expected tables present")

            # ── Check alembic_version head revision ─────────────────────
            try:
                r = await conn.execute(text("SELECT version_num FROM alembic_version"))
                head = r.scalar()
                if head == _EXPECTED_HEAD:
                    _ok("schema.revision", f"head={head}")
                else:
                    _fail("schema.revision", f"expected={_EXPECTED_HEAD}, actual={head}")
                    errors += 1
            except Exception as e:
                _fail("schema.revision", f"cannot read alembic_version: {e}")
                errors += 1

            # ── Check vector extension ──────────────────────────────────
            try:
                r = await conn.execute(
                    text(
                        "SELECT installed_version FROM pg_available_extensions WHERE name='vector'"
                    )
                )
                ext_ver = r.scalar()
                if ext_ver:
                    _ok("schema.vector", f"installed (version={ext_ver})")
                else:
                    _fail("schema.vector", "vector extension NOT installed")
                    errors += 1
            except Exception as e:
                _fail("schema.vector", f"cannot check vector extension: {e}")
                errors += 1
    except Exception as e:
        _fail("schema", f"connection failed: {e}")
        return 1

    return errors


async def check_runtime() -> int:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from app.core.database import PGCONN_ARGS, AsyncSessionLocal, engine
    from sqlalchemy import text

    errors = 0

    # ── Raw connection: verify statement cache is disabled ──────────────
    try:
        import asyncpg

        raw_conn = await asyncpg.connect(
            _db_url(),
            statement_cache_size=0,
            timeout=10,
            ssl=os.environ.get("DB_SSL_MODE", "require"),
        )
        await raw_conn.close()
        _ok("runtime.raw", "asyncpg.connect with statement_cache_size=0 succeeded")
    except Exception as e:
        _fail("runtime.raw", f"raw asyncpg.connect failed: {e}")
        errors += 1

    # ── Engine-based connection: SELECT 1 ────────────────────────────────
    try:
        async with engine.connect() as conn:
            r = await conn.execute(text("SELECT 1"))
            assert r.scalar() == 1
            _ok("runtime.engine", "SELECT 1 via engine.connect")
    except Exception as e:
        _fail("runtime.engine", str(e))
        errors += 1

    # ── Session-based connection: SELECT 1 ───────────────────────────────
    try:
        async with AsyncSessionLocal() as s:
            r = await s.execute(text("SELECT 1 AS a"))
            assert r.scalar() == 1
            _ok("runtime.session", "SELECT 1 via AsyncSessionLocal")
    except Exception as e:
        _fail("runtime.session", str(e))
        errors += 1

    # ── Verify engine uses a valid pool class ───────────────────────────
    from sqlalchemy.pool import NullPool, QueuePool

    pool = engine.pool
    pool_name = type(pool).__name__
    if isinstance(pool, NullPool):
        _ok("runtime.poolclass", "NullPool (session-mode PgBouncer)")
    elif isinstance(pool, QueuePool):
        _ok("runtime.poolclass", f"QueuePool(size={pool.size()}, overflow={pool._max_overflow})")
    else:
        _fail("runtime.poolclass", f"unexpected poolclass={pool_name}")
        errors += 1

    ssl_val = PGCONN_ARGS.get("ssl", "not-set")
    _ok("runtime.ssl", f"ssl={ssl_val}")

    stmt_cache = PGCONN_ARGS.get("statement_cache_size", "not-set")
    if stmt_cache != 0:
        _fail("runtime.stmt_cache", f"statement_cache_size={stmt_cache}, expected 0")
        errors += 1
    else:
        _ok("runtime.stmt_cache", "statement_cache_size=0")

    if errors == 0:
        _ok("runtime", "runtime DB validation passed")
    return errors


def main() -> int:
    check = sys.argv[1] if len(sys.argv) > 1 else ""
    url = _db_url()
    masked = url.replace("+asyncpg", "")
    if "@" in masked:
        masked = masked.split("@")[0].split("://")[0] + "://****@" + masked.split("@", 1)[1]
    print(f"  Database: {masked}")

    if check == "dns":
        return check_dns()
    elif check == "tcp":
        return check_tcp()
    elif check == "auth":
        return asyncio.run(check_auth())
    elif check == "pgbouncer":
        return check_pgbouncer()
    elif check == "schema":
        return asyncio.run(check_schema())
    elif check == "runtime":
        return asyncio.run(check_runtime())
    else:
        print(f"Unknown check: {check}", file=sys.stderr)
        print("Usage: python -m scripts.ci_db_check CHECK_NAME", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
