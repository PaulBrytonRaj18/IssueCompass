"""
Pre-deployment CI validation suite for IssueCompass.

Run from the backend/ directory:
    python -m scripts.ci_validate

Environment must have DATABASE_URL set (pointing to a running PostgreSQL).
Other env vars (SECRET_KEY, GITHUB_TOKEN, etc.) should also be set for
realistic config validation.

Exit codes:
    0 — all checks passed
    1 — one or more checks failed
"""

import asyncio
import logging
import os
import sys

# Configure logging before any app imports
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-7s %(name)s %(message)s",
)
logger = logging.getLogger("ci_validate")

# Suppress noisy app-level logs during validation
logging.getLogger("app").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


# ── Helpers ────────────────────────────────────────────────────────────────


def _mask_db_url(raw: str) -> str:
    if "@" in raw:
        return raw.split("@")[0].split("://")[0] + "://****@" + raw.split("@", 1)[1]
    return raw


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


# ── Checks ─────────────────────────────────────────────────────────────────


async def check_network() -> int:
    """Validate DNS resolution and TCP reachability for the database host."""
    import socket
    failed = 0
    print("\n--- 0. Database Network Diagnostics ---")

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        _fail("network", "DATABASE_URL is not set")
        return 1

    # Parse hostname and port from URL
    from urllib.parse import urlparse
    parsed = urlparse(db_url.replace("+asyncpg", ""))
    host = parsed.hostname or "unknown"
    port = parsed.port or 5432

    print(f"  Target: {_mask_db_url(db_url)}")
    print(f"  Host:   {host}")
    print(f"  Port:   {port}")

    # DNS resolution
    try:
        addrs = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        has_ipv4 = any(a[0] == socket.AF_INET for a in addrs)
        has_ipv6 = any(a[0] == socket.AF_INET6 for a in addrs)
        print(f"  DNS:    {len(addrs)} address(es) [IPv4={has_ipv4} IPv6={has_ipv6}]")
        for a in addrs:
            family = "IPv6" if a[0] == socket.AF_INET6 else "IPv4"
            print(f"          {family}: {a[4][0]}")
        if not has_ipv4:
            print("  WARN:   No IPv4 A record — connection will fail on IPv4-only networks")
    except socket.gaierror as e:
        _fail("DNS resolution", f"cannot resolve {host}: {e}")
        return 1

    # TCP connectivity (via IPv4 fallback if available)
    connected = False
    for family, af_label in [(socket.AF_INET, "IPv4"), (socket.AF_INET6, "IPv6")]:
        try:
            family_addrs = socket.getaddrinfo(host, port, family, socket.SOCK_STREAM)
        except socket.gaierror:
            continue
        for addr in family_addrs:
            s = socket.socket(family, socket.SOCK_STREAM)
            s.settimeout(5)
            try:
                s.connect(addr[4])
                print(f"  TCP:    {af_label} connected to {addr[4]}")
                connected = True
                s.close()
                break
            except OSError as e:
                print(f"  TCP:    {af_label} {addr[4][0]} — {e}")
                s.close()
        if connected:
            break

    if not connected:
        _fail("TCP connectivity", "could not connect to database host on any address family")
        return 1

    _ok("network", f"DNS + TCP reachable — host={host} port={port}")
    return failed


async def check_async_engine() -> int:
    """Validate async engine creation and basic connectivity."""
    failed = 0
    print("\n--- 1. Async Engine + PgBouncer Compatibility ---")

    from app.core.database import PGCONN_ARGS, AsyncSessionLocal, engine, get_pool_status
    from sqlalchemy import text

    # Verify engine exists
    if engine is None:
        _fail("engine", "engine is None")
        return 1
    _ok("engine", f"engine created, target={_mask_db_url(str(engine.url))}")

    # Verify PgBouncer-safe connect_args from the engine's configuration
    try:
        if PGCONN_ARGS.get("statement_cache_size") != 0:
            _fail("PgBouncer", "statement_cache_size is not 0")
            failed += 1
        elif PGCONN_ARGS.get("prepared_statement_cache_size") != 0:
            _fail("PgBouncer", "prepared_statement_cache_size is not 0")
            failed += 1
        else:
            _ok("PgBouncer", "statement_cache_size=0 and prepared_statement_cache_size=0")
    except Exception as e:
        _fail("PgBouncer", f"could not inspect PGCONN_ARGS: {e}")
        failed += 1

    # Verify NullPool is used (PgBouncer-compatible)
    try:
        poolclass_name = type(engine.pool).__name__
        if poolclass_name != "NullPool":
            _fail("Pool class", f"expected NullPool, got {poolclass_name}")
            failed += 1
        else:
            _ok("Pool class", "NullPool — session pooler compatible")
    except Exception as e:
        _fail("Pool class", str(e))
        failed += 1

    # Test SELECT 1
    try:
        async with engine.connect() as conn:
            r = await conn.execute(text("SELECT 1"))
            val = r.scalar()
            assert val == 1, f"expected 1, got {val}"
            _ok("connectivity", "SELECT 1 OK")
    except Exception as e:
        _fail("connectivity", f"SELECT 1 failed: {e}")
        failed += 1

    # Test pool introspection — NullPool expected
    try:
        status = await get_pool_status()
        assert isinstance(status, dict), f"expected dict, got {type(status)}"
        assert status.get("poolclass") == "NullPool", f"expected NullPool, got {status}"
        _ok("pool status", "NullPool — no pooling")
    except Exception as e:
        _fail("pool status", str(e))
        failed += 1

    # Test concurrent sessions
    try:
        for label in ("session-1", "session-2"):
            async with AsyncSessionLocal() as s:
                r = await s.execute(text("SELECT 1 AS a"))
                assert r.scalar() == 1
            _ok(label)
    except Exception as e:
        _fail("concurrent sessions", str(e))
        failed += 1

    return failed


async def check_db_reconcile() -> int:
    """Validate db_reconcile script handles fresh DB gracefully."""
    failed = 0
    print("\n--- 2. db_reconcile (fresh DB) ---")

    exit_code = os.system(f"{sys.executable} -m scripts.db_reconcile")
    if exit_code != 0:
        _fail("db_reconcile", f"exit code {exit_code}")
        failed += 1
    else:
        _ok("db_reconcile", "fresh database handled correctly")

    return failed


async def check_alembic() -> int:
    """Validate Alembic migrations run cleanly."""
    failed = 0
    print("\n--- 3. Alembic Migrations ---")

    import subprocess

    # Check current state
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "current"],
        capture_output=True, text=True,
    )
    print(r.stdout)
    if r.returncode != 0:
        _fail("alembic current", r.stderr.strip())
        failed += 1
    else:
        _ok("alembic current")

    # Run migrations
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True, text=True,
    )
    print(r.stdout)
    if r.returncode != 0:
        _fail("alembic upgrade head", r.stderr.strip())
        failed += 1
    else:
        _ok("alembic upgrade head")

    # Verify final state
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "current"],
        capture_output=True, text=True,
    )
    print(r.stdout)
    if r.returncode != 0:
        _fail("alembic current (post-upgrade)", r.stderr.strip())
        failed += 1
    else:
        _ok("alembic current (post-upgrade)")

    return failed


async def check_schema() -> int:
    """Validate schema introspection finds expected tables."""
    failed = 0
    print("\n--- 4. Schema Introspection ---")

    from app.core.database import engine
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            r = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' ORDER BY table_name"
            ))
            tables = [row[0] for row in r]
            print(f"  Tables ({len(tables)}): {tables}")

            expected = {
                "users", "repositories", "issues",
                "saved_searches", "alembic_version",
            }
            missing = expected - set(tables)
            if missing:
                _fail("schema", f"missing tables: {missing}")
                failed += 1
            else:
                _ok("schema", f"{len(tables)} tables, all expected present")
    except Exception as e:
        _fail("schema", str(e))
        failed += 1

    return failed


# ── Main ───────────────────────────────────────────────────────────────────


async def main() -> int:
    total = 0

    print("=" * 55)
    print("IssueCompass — Pre-Deployment CI Validation")
    print("=" * 55)
    print(f"Python: {sys.version.split()[0]}")
    print(f"Database URL: {_mask_db_url(os.environ.get('DATABASE_URL', 'NOT SET'))}")
    print()

    total += await check_network()
    total += await check_async_engine()
    total += await check_db_reconcile()
    total += await check_alembic()
    total += await check_schema()

    print()
    print("=" * 55)
    if total == 0:
        print("ALL CHECKS PASSED")
    else:
        print(f"{total} CHECK(S) FAILED")
    print("=" * 55)

    return 0 if total == 0 else 1


def cli():
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


if __name__ == "__main__":
    cli()
