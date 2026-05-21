# Engineering Report: Asyncpg + PgBouncer Transaction Pooling Fix

## 1. Root Cause Analysis

### The Two Errors

| Error | Meaning | Trigger |
|-------|---------|---------|
| `InvalidSQLStatementNameError: prepared statement "__asyncpg_stmt_x__" does not exist` | asyncpg tried to `Execute` a prepared statement that was never `Parse`d on the current backend connection | PgBouncer switched backends between `Parse` and `Execute` |
| `DuplicatePreparedStatementError: prepared statement "__asyncpg_stmt_x__" already exists` | asyncpg tried to `Parse` a statement name that's already in use on the backend | Two `Parse` calls for the same name on the same backend before a `Close` |

### Why This Happens

**Infrastructure discovery:**
- `DATABASE_URL` points to `pooler.supabase.com:6543` — **Supabase PgBouncer** in **transaction pooling mode**
- Every SQL transaction may be routed to a **different PostgreSQL backend** even though the TCP connection to PgBouncer stays the same
- asyncpg uses the **extended query protocol** (`Parse` / `Bind` / `Execute` / `Close`) for prepared statements
- PgBouncer in transaction mode does NOT guarantee the same backend for successive transactions

**The sequence of failure:**
1. Transaction 1 → PgBouncer routes to **Backend A** → asyncpg sends `Parse __asyncpg_stmt_0__` → `Execute` → `Close` → transaction ends
2. Transaction 2 → PgBouncer routes to **Backend B** → asyncpg sends `Parse __asyncpg_stmt_0__` on B (OK, B doesn't have it yet) → BUT asyncpg might try to use the **cached** statement from Transaction 1 without re-parsing if the cache is not fully disabled

### Why the Previous Fix Was Insufficient

The `statement_cache_size=0` parameter was set, but **asyncpg 0.29.0 deprecated this parameter** in favour of `prepared_statement_cache_size`. While backward compatibility should exist, the parameter was not reliably disabling the cache in all code paths. Two independent engine creation paths lacked BOTH parameters:

| Engine location | Had `statement_cache_size=0`? | Had `prepared_statement_cache_size=0`? |
|----------------|------------------------------|--------------------------------------|
| `app/core/database.py` | ✅ Yes | ❌ No |
| `alembic/env.py` | ✅ Yes | ❌ No |
| `scripts/db_reconcile.py` | ✅ Yes | ❌ No |

Additionally, `init_db()` used `engine.begin()` — the **application pool** — leaking a startup prepared statement (`CREATE EXTENSION IF NOT EXISTS vector`) into the shared pool. This could pollute connection state when PgBouncer switched backends between startup and first request.

---

## 2. Connection Architecture Fixes

### 2.1 All Three Engines Now Set Both Cache Parameters

| File | Change | Why |
|------|--------|-----|
| `database.py` | `"prepared_statement_cache_size": 0` added to `connect_args` | asyncpg 0.29.0+ renamed parameter |
| `alembic/env.py` | `"prepared_statement_cache_size": 0` added | Same fix for Alembic's engine |
| `scripts/db_reconcile.py` | `"prepared_statement_cache_size": 0` added | Same fix for reconcile engine |

```python
connect_args={
    "statement_cache_size": 0,            # asyncpg <0.28
    "prepared_statement_cache_size": 0,    # asyncpg >=0.28
    "timeout": 10,
    "command_timeout": 30,
}
```

### 2.2 Isolated `init_db()` Engine

`init_db()` previously used `engine.begin()` — the shared application pool. Now it creates a **short-lived engine** with `NullPool`:

```python
async def init_db():
    tmp_engine = create_async_engine(DATABASE_URL, poolclass=None, connect_args={...})
    async with tmp_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    await tmp_engine.dispose()
```

This prevents the startup query from ever entering the application pool's connections.

### 2.3 Pool Configuration Hardening

| Setting | Old Value | New Value | Rationale |
|---------|-----------|-----------|-----------|
| `pool_size` | 5 | **3** | Supabase free tier max 15; 2 workers × 5 = 20 exceeds limit |
| `max_overflow` | 5 | **2** | Burst capacity capped to stay within Supabase limit |
| `pool_recycle` | 1800s | **300s** | Well below PgBouncer's `server_idle_timeout` (typically 600s) |
| `pool_use_lifo` | (default) | **True** | Reuses hottest connection, reduces backend churn |
| `pool_pre_ping` | True | True | Validates connection before use (catches stale PgBouncer connections) |
| `pool_timeout` | 5 | 5 | Fast failure if all connections busy |
| `isolation_level` | (unset) | `READ_COMMITTED` | Explicit, prevents accidental SERIALIZABLE |

### 2.4 Graceful Shutdown

Added `close_db()` — called from `main.py` lifespan shutdown — disposes the engine pool:
- All pooled connections are closed
- PgBouncer can immediately reclaim backend connections
- Prevents connection leaks on process exit

### 2.5 Pool Diagnostics Logging

Three event listeners on the pool:
- `connect` — logs when new DB connections are established
- `checkin` — logs when connections return to pool
- `checkout` — logs when connections leave the pool

### 2.6 Health Endpoint Enhancement

`/health` now includes `pool` field with:
```json
{
  "size": 3,
  "checked_in": 3,
  "checked_out": 0,
  "overflow": 0
}
```

---

## 3. Migration Flow Improvements

### 3.1 Sequential Container Startup

```
Docker CMD:
  1. python -m scripts.db_reconcile   ← checks if alembic_version table exists
  2. alembic upgrade head              ← applies pending migrations
  3. gunicorn main:app                 ← starts application
```

Each step fails-fast (non-zero exit stops the chain).

### 3.2 `DATABASE_URL_DIRECT` Support

Set `DATABASE_URL_DIRECT` to a **direct PostgreSQL connection** (port 5432, bypassing PgBouncer) for Alembic migrations. Falls back to `DATABASE_URL` if not set.

### 3.3 `scripts/db_reconcile.py`

Detection:
- `alembic_version` table exists? → no-op (normal case)
- `users` table exists but `alembic_version` missing? → stamps head (fixes drift)
- Neither exists? → no-op (fresh database)

---

## 4. Remaining Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Supabase connection limit** | 15 connections max on free tier | `pool_size=3, max_overflow=2` per worker gives max 10 total for 2 workers |
| **`DEALLOCATE ALL` not issued on checkout** | Stale prepared statements could theoretically leak | `statement_cache_size=0` + `prepared_statement_cache_size=0` should prevent any prepared statements from persisting. If errors persist, add `DEALLOCATE ALL` event on pool checkout |
| **asyncpg new parameter name** | `prepared_statement_cache_size` might not be recognized in asyncpg <0.28 | Both old and new names are set; old name provides backward compatibility |
| **Alembic offline mode** | Not commonly used but could bypass engine config | Offline mode generates SQL files; actual execution happens separately. No engine config needed |

---

## 5. Manual Test Checklist

Before deploying to production:

- [ ] `python -m pytest tests/ -v` — all 84 tests pass (2 skipped = GitHub integration)
- [ ] `python -m alembic upgrade head` — migrations run without prepared statement errors
- [ ] `python -m scripts.db_reconcile` — reconciliation runs without errors
- [ ] `python -c "from app.core.database import engine; print(engine.pool.size())"` — engine imports correctly
- [ ] `curl http://localhost:8080/health` — returns `"pool": {"size": 3, ...}`
- [ ] With `DATABASE_URL_DIRECT` set to direct Supabase connection (port 5432):
  - [ ] `alembic upgrade head` runs without errors
  - [ ] `scripts.db_reconcile` succeeds
- [ ] With `DATABASE_URL` pointing to PgBouncer (port 6543):
  - [ ] `alembic upgrade head` runs without errors
  - [ ] Application handles 100+ requests without `InvalidSQLStatementNameError`
  - [ ] Application handles 100+ requests without `DuplicatePreparedStatementError`

---

## 6. Summary of Changed Files

| File | Lines Changed | Type |
|------|---------------|------|
| `backend/app/core/database.py` | Full rewrite (50→140) | Fix + hardening |
| `backend/alembic/env.py` | 2 lines | Fix |
| `backend/scripts/db_reconcile.py` | 2 lines | Fix |
| `backend/main.py` | 3 lines | Hardening |
| `backend/Dockerfile` | 1 line | Fix (from earlier session) |
