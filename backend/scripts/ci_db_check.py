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
    try:
        conn = await asyncpg.connect(url, statement_cache_size=0, timeout=10)
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
    from sqlalchemy.pool import NullPool

    errors = 0

    stmt = PGCONN_ARGS.get("statement_cache_size")
    if stmt != 0:
        _fail("pgbouncer", f"statement_cache_size={stmt}, expected 0")
        errors += 1
    else:
        _ok("pgbouncer", "statement_cache_size=0")

    if "prepared_statement_cache_size" in PGCONN_ARGS:
        _fail("pgbouncer", "prepared_statement_cache_size present but NOT a valid asyncpg param")
        errors += 1
    else:
        _ok("pgbouncer", "prepared_statement_cache_size absent (correct — not a valid param)")

    pool = engine.pool
    if not isinstance(pool, NullPool):
        _fail("pgbouncer", f"poolclass={type(pool).__name__}, expected NullPool")
        errors += 1
    else:
        _ok("pgbouncer", "poolclass=NullPool")

    return errors


async def check_schema() -> int:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from app.core.database import engine
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            r = await conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema='public' ORDER BY table_name"
                )
            )
            tables = [row[0] for row in r]
            print(f"  Tables ({len(tables)}): {tables}")
            expected = {"users", "repositories", "issues", "saved_searches", "alembic_version", "saved_issues"}
            missing = expected - set(tables)
            if missing:
                _fail("schema", f"missing tables: {missing}")
                return 1
            _ok("schema", f"all {len(expected)} expected tables present")
            return 0
    except Exception as e:
        _fail("schema", str(e))
        return 1


async def check_runtime() -> int:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from app.core.database import AsyncSessionLocal, engine
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            r = await conn.execute(text("SELECT 1"))
            assert r.scalar() == 1
            print("  engine.connect SELECT 1: OK")
    except Exception as e:
        _fail("runtime", f"engine.connect: {e}")
        return 1

    try:
        async with AsyncSessionLocal() as s:
            r = await s.execute(text("SELECT 1 AS a"))
            assert r.scalar() == 1
            print("  session SELECT 1: OK")
    except Exception as e:
        _fail("runtime", f"session: {e}")
        return 1

    _ok("runtime", "asyncpg connectivity verified")
    return 0


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
