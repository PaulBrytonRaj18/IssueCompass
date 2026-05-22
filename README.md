# IssueCompass

**Match open-source contributors to issues they can actually solve.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](CONTRIBUTING.md)

---

## The Problem

Developers want to contribute to open source but face a discovery gap:

- **Contributors** browse GitHub aimlessly, wasting hours finding issues matching their skill set
- **Maintainers** tag issues as "good first issue" but attract contributors without the right skills
- **Existing tools** (GitHub Explore, goodfirstissue.dev) are generic lists — zero personalization, zero intelligence

## The Solution

IssueCompass analyzes your **actual GitHub activity** to build a personal skill fingerprint, then uses **pgvector semantic similarity search** to match you with open issues across thousands of repositories that align with your demonstrated abilities.

```
GitHub Login  →  Fetch repos & activity  →  Build skill vector  →  Semantic match  →  Personalized feed
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                          │
│  Landing · Dashboard · Search · Trending · Saved · Maintainer       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  HTTP / JSON
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI on Uvicorn)                      │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌────────────────────┐  │
│  │ Auth     │  │ Issues   │  │ Search    │  │ Maintainer         │  │
│  │ (JWT)    │  │ (Matches)│  │ (NL→SQL)  │  │ Dashboard          │  │
│  └──────────┘  └──────────┘  └───────────┘  └────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │                    Core Services                                  ││
│  │  GitHub API · Skill Analysis · Matching Engine · Scoring Engine  ││
│  │  AI Service (Groq LLM) · Search Parser (NL→Intent)               ││
│  └──────────────────────────────────────────────────────────────────┘│
└───────────────────┬──────────────────────────────────────┬───────────┘
                    │                                      │
                    ▼                                      ▼
         ┌──────────────────┐                  ┌──────────────────┐
         │   PostgreSQL     │                  │     Redis        │
         │   (pgvector)     │                  │                  │
         │                  │                  │  • API cache     │
         │  • Users         │                  │  • Rate limiting │
         │  • Repos         │                  │  • ARQ worker    │
         │  • Issues        │                  │    broker        │
         │  • Vectors(128)  │                  │  • Cache stats   │
         └──────────────────┘                  └──────────────────┘
```

### Backend Stack

| Layer | Technology | Purpose |
|---|---|---|
| Framework | FastAPI 0.111 | Async Python web framework |
| ORM | SQLAlchemy 2.0 | Async PostgreSQL access |
| Database | PostgreSQL 16 + pgvector | Relational data + 128-dim vector search |
| Cache | Redis 7 | API caching, rate limiting, job broker |
| AI | Groq (Llama 3.3 70B) | Skill extraction, NL query parsing, explanations |
| Auth | JWT (HS256) + GitHub OAuth (NextAuth) | Stateless API auth |
| Worker | ARQ 0.26 | Background issue indexing |
| HTTP | httpx | GitHub REST API client |

---

## Redis Integration

Redis serves three distinct roles in production:

### 1. API Response Cache (`app/core/cache.py`)

Reduces latency by caching expensive computations (vector similarity, GitHub API calls, NL parsing). Gracefully degrades when Redis is unavailable — the app keeps working, just slower.

| Endpoint | Cache Key Pattern | TTL | Why Cached |
|---|---|---|---|
| `GET /issues/matches` | `ic:matches:{user}:{lang}:{label}:{limit}:{offset}` | 5 min | Vector similarity + scoring (200-500ms) |
| `GET /issues/search` | `ic:search:{query}:{lang}:{diff}:{label}:{limit}:{offset}` | 30 min | DB query + GitHub API fallback |
| `GET /issues/trending` | `ic:trending:{lang}:{limit}` | 1 hour | Rate-limited GitHub API calls |
| `GET /issues/smart-search` | `ic:smart:{query}:{diff}:{label}:{limit}:{offset}:{auth\|anon}` | 10 min | NL parsing + semantic scoring |

**Features:**
- Namespace prefix (`ic:`) to avoid key collisions in shared Redis
- Probabilistic early expiry (stampede protection) — refreshes cache in background before TTL hits zero
- Hit/miss counters exposed at `/metrics`
- Full graceful degradation: `cache_get()` returns `None`, `cache_set()` returns `False` when Redis is down

### 2. Rate Limiting Backend (`app/core/ratelimit.py`)

Uses slowapi with Redis for shared rate counters across all workers:
- **Default:** 30 requests/minute per user (JWT `sub`) or per IP
- **Keys:** `user:{id}` for authenticated, `ip:{addr}` for anonymous
- Without Redis, rate limits reset on restart and don't coordinate between workers

### 3. Background Job Queue (`app/worker.py`)

ARQ (Redis-backed job queue) runs offline tasks:
- `full_index` — Index all languages with "good first issue" + "help wanted" labels, then invalidates `trending:*` cache
- `index_language_issues` — Fetch issues from GitHub for one language/label pair, upsert into DB with skill vectors
- `check_saved_searches` — Periodically re-evaluate saved searches and log new results

### Graceful Degradation

All Redis operations are wrapped in try/except. When Redis is unreachable:
- **Cache reads** return `None` → routes recompute data from DB/GitHub
- **Cache writes** return `False` → data served fresh next request
- **Rate limiting** falls to slowapi's in-memory fallback
- **ARQ worker** fails to start (Redis is mandatory for the job queue)
- **Health endpoint** reports `"redis": false` in `/health` response

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local backend dev)
- Node.js 20+ (for local frontend dev)
- GitHub Personal Access Token ([create one](https://github.com/settings/tokens), scopes: `public_repo`, `read:user`)

### One-command Start (Docker)

```bash
cp .env.example .env
# Edit .env: set GITHUB_TOKEN, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GROQ_API_KEY
docker compose up --build
```

Access:
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API docs:** http://localhost:8000/docs
- **Health:** http://localhost:8000/health
- **Metrics:** http://localhost:8000/metrics

### Local Development (without Docker)

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env  # fill in secrets
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend
npm install
cp ../.env.example .env.local  # fill in secrets
npm run dev
```

### Run the ARQ Worker

```bash
cd backend && source venv/bin/activate
arq app.worker.WorkerSettings
# Or: python -m app.worker
```

---

## Environment Variables

### Redis

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379` | Connection string (use `rediss://` for TLS) |
| `REDIS_SOCKET_TIMEOUT` | `3` | Socket read/write timeout (seconds) |
| `REDIS_SOCKET_CONNECT_TIMEOUT` | `3` | Connection timeout (seconds) |
| `REDIS_RETRY_ON_TIMEOUT` | `true` | Auto-retry on timeout |
| `REDIS_MAX_CONNECTIONS` | `20` | Connection pool size |
| `REDIS_PREFIX` | `ic:` | Cache key namespace prefix |

### Full List

See [`.env.example`](.env.example) for all required and optional variables.

---

## API Overview

All production endpoints under `/api/v1`:

| Endpoint | Auth | Description |
|---|---|---|
| `POST /auth/github/callback` | No | GitHub OAuth → JWT |
| `GET /auth/me` | JWT | Current user profile |
| `POST /auth/refresh` | JWT | Rotate access token |
| `POST /github/analyze/{username}` | JWT | Build skill fingerprint from repos |
| `GET /github/user/{username}` | No | Proxy GitHub user profile |
| `GET /github/fingerprint` | JWT | Get stored skill fingerprint |
| `GET /issues/matches` | JWT | Personalized issue matches |
| `POST /issues/index` | No | Trigger background indexing |
| `POST /issues/save/{id}` | JWT | Save an issue |
| `GET /issues/saved` | JWT | List saved issues |
| `GET /issues/search` | No | Keyword + GitHub fallback |
| `GET /issues/trending` | No | Trending issues |
| `GET /issues/smart-search` | Optional | NL semantic search |
| `GET /issues/stats` | No | Platform statistics |
| `GET /searches/suggestions` | No | Autocomplete |
| `POST /searches/save` | JWT | Save a search |
| `GET /searches/` | JWT | List saved searches |
| `GET /searches/{id}` | JWT | Get saved search |
| `PUT /searches/{id}` | JWT | Update saved search |
| `DELETE /searches/{id}` | JWT | Delete saved search |
| `POST /searches/{id}/check` | JWT | Check for new results |
| `GET /maintainer/overview` | JWT | Repos + issue stats |
| `GET /maintainer/repos/{id}` | JWT | Repo detail + issues |
| `GET /maintainer/repos/{id}/contributors` | JWT | Top contributor matches |

---

## Testing

```bash
# Backend (58 tests, 2 skipped — need live GitHub credentials)
cd backend && source venv/bin/activate
pytest -v

# Frontend lint + type check
cd frontend
npm run lint
npx tsc --noEmit
```

Tests override `AI_ENABLED=false` and `GROQ_API_KEY=""` to avoid real LLM calls. Redis connectivity is not required — all cache operations degrade gracefully and return `None`/`False`.

---

## CI/CD Pipeline

Every push and PR runs through an 8-job **pre-deployment validation pipeline** on GitHub Actions. Broken deployments never reach Render.

```
Push Code
  ↓
env-check (verify all 9 secrets exist)
  ├── backend-lint   (ruff + mypy)
  ├── frontend       (npm ci + lint + tsc)
  ├── backend-test   (104 pytest, mocked DB)
  └── db-validate    (pgvector, async engine, PgBouncer compat, Alembic, schema)
      ├── startup-validate  (boot FastAPI, hit /health — DB + Redis)
      └── docker-validate   (build image, run container, hit /health)
           └── deploy  (Render Deploy Hook — main branch only)
```

| Job | What it validates |
|---|---|
| `env-check` | All 9 secrets exist (DATABASE_URL, REDIS_URL, SECRET_KEY, GITHUB_TOKEN, GITHUB_CLIENT_ID/SECRET, GROQ_API_KEY, JINA_API_KEY, RENDER_DEPLOY_HOOK_URL) |
| `backend-lint` | ruff (PEP 8) + mypy (strict) — zero errors |
| `frontend` | npm ci + lint + TypeScript `--noEmit` |
| `backend-test` | 104 pytest (mocked DB/Redis, no services needed) |
| `db-validate` | Real pgvector connection, `statement_cache_size=0` PgBouncer safety, `db_reconcile` on fresh DB, Alembic migrations, schema introspection |
| `startup-validate` | Actual FastAPI boot with uvicorn, Alembic pre-applied, `/health` validates status+DB+Redis+version+pool |
| `docker-validate` | Build Docker image from `backend/Dockerfile`, run container with `--network host`, validate `/health` |
| `deploy` | Fires only on `main` + `push` after all 7 gates pass. Curl POST to `RENDER_DEPLOY_HOOK_URL` |

The `startup-validate` and `docker-validate` jobs are gated behind `backend-lint`, `backend-test`, and `db-validate` — they only run if code quality and database checks pass first.

DB validation uses `pgvector/pgvector:pg16` and `redis:7-alpine` as GitHub Actions service containers. A reusable [`scripts/ci_validate.py`](backend/scripts/ci_validate.py) runs the full async engine + PgBouncer + Alembic + schema suite.

---

## Deployment

### Docker Compose (recommended)

```bash
docker compose up --build -d
```

Services: `db` (pgvector/pg16), `redis` (redis:7-alpine), `backend` (FastAPI), `frontend` (Next.js).

### Production Checklist

1. Set `SECRET_KEY` to a secure random value (`python3 -c "import secrets; print(secrets.token_hex(32))"`)
2. Set `REDIS_URL` to your managed Redis instance (Upstash, ElastiCache, Redis Cloud with `rediss://`)
3. Set `DATABASE_URL` to your managed PostgreSQL (Supabase, RDS, etc.)
4. Set `FRONTEND_URL` for CORS configuration
5. Enable AI: `GROQ_API_KEY` + `AI_ENABLED=true`
6. Verify with `curl /health`

---

## Roadmap

- Email digest of new matched issues
- Browser extension (GitHub sidebar integration)
- CLI tool for terminal-based matching
- Slack/Discord bot for issue notifications
- Contribution streak tracking and gamification

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines. All contributions welcome — features, bug fixes, tests, docs.

---

## License

[MIT](LICENSE) — Copyright (c) 2026 Paul Bryton Raj
