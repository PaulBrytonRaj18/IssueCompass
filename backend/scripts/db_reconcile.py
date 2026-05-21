"""
Database reconciliation script for production Alembic safety.

Purpose:
  Detect when application tables exist but the alembic_version table is missing,
  and safely stamp the current Alembic head to prevent DuplicateTableError
  during migration.

Background:
  If application tables were created outside Alembic (e.g., by an earlier
  version using Base.metadata.create_all(), or by manual DDL), Alembic will
  try to recreate them because it has no record of the current schema state.
  This causes "relation already exists" errors during deployment.

Usage:
  python -m scripts.db_reconcile

Environment:
  DATABASE_URL or DATABASE_URL_DIRECT — database connection string
  SKIP_DB_RECONCILE — set to "true" to skip reconciliation (for local dev)
"""

import asyncio
import os
import sys


async def reconcile() -> int:
    if os.environ.get("SKIP_DB_RECONCILE", "").lower() in ("true", "1", "yes"):
        print("DB_RECONCILE: Skipped (SKIP_DB_RECONCILE is set)")
        return 0

    db_url = os.environ.get("DATABASE_URL_DIRECT") or os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("DB_RECONCILE: No DATABASE_URL found, skipping")
        return 0

    if "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    # ── Retry loop ───────────────────────────────────────────────────────
    # PgBouncer transaction pooling can cause transient prepared-statement
    # conflicts when multiple deploy processes connect simultaneously.
    # Retry with backoff to survive these race conditions.
    import asyncio

    max_retries = 3
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        engine = create_async_engine(
            db_url,
            poolclass=NullPool,
            connect_args={
                "prepared_statement_cache_size": 0,
                "statement_cache_size": 0,
                "timeout": 10,
                "command_timeout": 30,
            },
        )
        try:
            print(f"DB_RECONCILE: Attempt {attempt}/{max_retries} — connecting...")
            async with engine.connect() as conn:
                result = await conn.execute(
                    text(
                        "SELECT EXISTS ("
                        "  SELECT FROM information_schema.tables "
                        "  WHERE table_name = 'alembic_version'"
                        ")"
                    )
                )
                alembic_version_exists = result.scalar()

                if alembic_version_exists:
                    print("DB_RECONCILE: alembic_version table found — no reconciliation needed")
                    return 0

                result = await conn.execute(
                    text(
                        "SELECT EXISTS ("
                        "  SELECT FROM information_schema.tables "
                        "  WHERE table_name = 'users'"
                        ")"
                    )
                )
                users_exists = result.scalar()

                if not users_exists:
                    print("DB_RECONCILE: Fresh database — no reconciliation needed")
                    return 0

                print(
                    "DB_RECONCILE: Tables exist but alembic_version is missing — "
                    "stamping head to prevent DuplicateTableError"
                )
                # Success — break out of retry loop
                break

        except Exception as e:
            last_error = e
            error_type = type(e).__name__
            print(
                f"DB_RECONCILE: Attempt {attempt}/{max_retries} failed "
                f"[{error_type}]: {e}",
                file=sys.stderr,
            )
            if attempt < max_retries:
                wait = attempt * 2  # linear backoff: 2s, 4s, ...
                print(f"DB_RECONCILE: Retrying in {wait}s...")
                await asyncio.sleep(wait)
            else:
                print(
                    f"DB_RECONCILE: All {max_retries} attempts failed — "
                    f"reconciliation will be retried on next deploy cycle",
                    file=sys.stderr,
                )
                return 1
        finally:
            try:
                await engine.dispose()
            except Exception:
                pass  # engine may not have been fully created

    alembic_cfg_path = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", alembic_cfg_path, "stamp", "head"],
        capture_output=False,
        env={**os.environ, "SKIP_DB_RECONCILE": "true"},
    )
    if result.returncode != 0:
        print(f"DB_RECONCILE: ERROR — alembic stamp head failed", file=sys.stderr)
        return 1

    print("DB_RECONCILE: Successfully stamped alembic_version to head")
    return 0


def main():
    exit_code = asyncio.run(reconcile())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
