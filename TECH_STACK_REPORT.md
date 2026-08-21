# IssueCompass — Tech Stack Report

> Generated: August 21, 2026
> Codebase: 25 backend source files (5,089 LOC) · 26 frontend source files (3,019 LOC) · 12 test files (2,791 LOC)

---

## Overview

IssueCompass is a full-stack application with a **Python/FastAPI backend**, a **Next.js/React frontend**, and **PostgreSQL + Redis** for data and caching. AI-powered features use Groq (LLM) and Jina (embeddings) for skill matching.

| Layer | Stack | Runtime |
|-------|-------|---------|
| Frontend | Next.js 14, React 18, TypeScript 5 | Node.js ≥18 |
| Backend | FastAPI, Python 3.12, Gunicorn | Python 3.12 |
| Database | PostgreSQL 16 + pgvector | TCP 5432 |
| Cache / Queue | Redis 7 + ARQ (async workers) | TCP 6379 |
| AI | Groq Cloud (LLaMA 3.3 70B) + Jina AI Embeddings v3 | HTTPS |
| Auth | NextAuth v4 (GitHub OAuth) + backend JWT | — |
| Deployment | Render (prod) / Docker Compose (local) | — |
| CI/CD | GitHub Actions (7-job pipeline) | — |

---

## 1. Frontend — `frontend/`

### Core Framework

| Package | Version | Purpose |
|---------|---------|---------|
| `next` | 14.2.21 | React framework (SSR, routing, API routes) |
| `react` / `react-dom` | 18.3.1 | UI library |
| `typescript` | 5.4.5 | Type safety |

### State & Data

| Package | Version | Purpose |
|---------|---------|---------|
| `@tanstack/react-query` | 5.100.11 | Server state management, caching, polling |
| `axios` | 1.7.2 | HTTP client with interceptors (auth, retry, rate-limit) |
| `next-auth` | 4.24.7 | GitHub OAuth via JWT sessions |

### UI Components

| Package | Version | Purpose |
|---------|---------|---------|
| `@radix-ui/react-dialog` | 1.1.0 | Accessible dialog/modal primitives |
| `@radix-ui/react-select` | 2.1.0 | Accessible select dropdown |
| `@radix-ui/react-tooltip` | 1.1.0 | Accessible tooltips |
| `lucide-react` | 0.383.0 | Icon library |
| `framer-motion` | 11.2.10 | Animations and transitions |
| `recharts` | 2.12.7 | Charts for skill fingerprint visualization |
| `tailwind-merge` | 2.3.0 | Tailwind class deduplication |
| `clsx` | 2.1.1 | Conditional classnames |

### Styling & Build

| Package | Version | Purpose |
|---------|---------|---------|
| `tailwindcss` | 3.4.4 | Utility-first CSS |
| `postcss` | 8.4.38 | CSS processing |
| `autoprefixer` | 10.4.19 | CSS vendor prefixing |
| `sharp` | 0.33.4 | Image optimization |

### Analytics

| Package | Version | Purpose |
|---------|---------|---------|
| `@vercel/analytics` | 2.0.1 | Web analytics (production) |

### Testing

| Package | Version | Purpose |
|---------|---------|---------|
| `vitest` | 2.1.9 | Test runner |
| `@testing-library/react` | 16.3.2 | React component testing |
| `@testing-library/jest-dom` | 6.9.1 | DOM assertion matchers |
| `@testing-library/user-event` | 14.6.1 | User interaction simulation |
| `jsdom` | 25.0.1 | Browser environment for tests |

### Architecture

```
frontend/src/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx          # Root layout with providers
│   ├── page.tsx            # Landing page
│   ├── providers.tsx       # Client-side provider stack
│   ├── dashboard/page.tsx  # Main dashboard (matches)
│   ├── trending/page.tsx   # Trending issues
│   ├── saved/page.tsx      # Saved issues
│   ├── profile/page.tsx    # User profile
│   ├── search/             # Search page
│   └── api/auth/           # NextAuth API routes
├── components/             # 9 reusable components
│   ├── Navbar.tsx
│   ├── IssueCard.tsx
│   ├── SkillFingerprint.tsx
│   ├── EmptyState.tsx
│   ├── ErrorBoundary.tsx
│   ├── SkeletonCard.tsx
│   ├── Spinner.tsx
│   ├── ThemeProvider.tsx
│   └── Toast.tsx
├── lib/
│   ├── api.ts              # Axios instance + interceptors
│   ├── types.ts            # TypeScript interfaces
│   ├── query-client.ts     # TanStack Query client config
│   ├── query-keys.ts       # Centralized query key factory
│   └── hooks/
│       ├── use-auth.ts     # Auth state hook
│       ├── use-issues.ts   # Issues/matches hook
│       └── use-github.ts   # GitHub analysis hook
├── styles/globals.css      # Global CSS + Tailwind base
└── middleware.ts           # Auth route protection
```

---

## 2. Backend — `backend/`

### Core Framework

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.111.0 | Async REST API framework |
| `uvicorn[standard]` | 0.29.0 | ASGI server |
| `gunicorn` | 22.0.0 | Process manager (production) |

### Database

| Package | Version | Purpose |
|---------|---------|---------|
| `sqlalchemy` | 2.0.30 | Async ORM with declarative mapping |
| `asyncpg` | 0.29.0 | Async PostgreSQL driver |
| `psycopg2-binary` | 2.9.12 | Sync PostgreSQL driver (scripts) |
| `alembic` | 1.13.1 | Schema migrations (4 revisions) |
| `pgvector` | 0.3.2 | Vector similarity search (128-dim HNSW) |

### Caching & Queue

| Package | Version | Purpose |
|---------|---------|---------|
| `redis[hiredis]` | 4.6.0 | Async Redis client with C parser |
| `arq` | 0.26.0 | Async Redis queue for background jobs |

### AI / ML

| Package | Version | Purpose |
|---------|---------|---------|
| `httpx` | 0.27.0 | Async HTTP client (GitHub API, Groq, Jina) |
| `numpy` | 1.26.4 | Vector math for cosine similarity |
| *(external)* | Groq API | LLaMA 3.3 70B for skill/issue analysis |
| *(external)* | Jina API | Embeddings v3 for semantic matching |

### Auth & Security

| Package | Version | Purpose |
|---------|---------|---------|
| `pyjwt` | 2.8.0 | JWT token creation/verification |
| `pydantic` | 2.7.1 | Data validation & serialization |
| `pydantic-settings` | 2.2.1 | Environment variable management |
| `slowapi` | 0.1.9 | Rate limiting (SlowAPI) |

### Observability

| Package | Version | Purpose |
|---------|---------|---------|
| `sentry-sdk` | 2.5.1 | Error tracking (0.1% sample rate) |
| `python-json-logger` | 4.1.0 | Structured JSON logging |

### Utilities

| Package | Version | Purpose |
|---------|---------|---------|
| `python-dotenv` | 1.0.1 | `.env` file loading |
| `tenacity` | 8.5.0 | Retry with exponential backoff |

### Architecture

```
backend/
├── main.py                 # FastAPI app, lifespan, middleware, routes
├── app/
│   ├── core/
│   │   ├── config.py       # Pydantic Settings (30+ env vars)
│   │   ├── database.py     # Async SQLAlchemy engine + pool
│   │   ├── cache.py        # Redis cache with stampede protection
│   │   ├── dependencies.py # JWT auth dependency injection
│   │   ├── monitoring.py   # Request logging + metrics
│   │   ├── ratelimit.py    # SlowAPI rate limit config
│   │   └── utils.py        # DateTime parsing utility
│   ├── models/
│   │   └── models.py       # 4 SQLAlchemy ORM models
│   ├── schemas/
│   │   └── schemas.py      # 18 Pydantic v2 models
│   ├── routes/
│   │   ├── auth.py         # 4 auth endpoints
│   │   ├── github.py       # 3 GitHub integration endpoints
│   │   └── issues.py       # 7 issue endpoints
│   ├── services/
│   │   ├── ai_service.py   # Groq LLM + Jina embeddings
│   │   ├── github_service.py    # GitHub REST API client
│   │   ├── matching_service.py  # pgvector + live hybrid matching
│   │   ├── scoring_service.py   # 12-dimension scoring weights
│   │   ├── search_service.py    # NLP query parsing + search
│   │   └── skill_service.py     # Skill fingerprinting pipeline
│   └── worker.py           # ARQ background worker (cron jobs)
├── scripts/
│   ├── db_reconcile.py     # Pre-migration schema validation
│   ├── ci_validate.py      # Pre-deployment validation suite
│   └── ci_db_check.py      # CI database health checks
├── alembic/                # 4 migration revisions
│   └── versions/
│       ├── 0001_initial_schema.py
│       ├── 0002_add_performance_indexes.py
│       ├── 0003_add_saved_searches_table.py
│       └── 0004_add_hnsw_vector_indexes.py
├── tests/                  # 237 test functions across 11 test files
│   ├── conftest.py
│   ├── test_routes.py
│   ├── test_cache.py
│   ├── test_scoring_service.py
│   ├── test_ai_service.py
│   ├── test_edge_cases.py
│   ├── test_github_service.py
│   ├── test_skill_service.py
│   ├── test_worker.py
│   ├── test_matching_service.py
│   └── test_search_service.py
├── requirements.txt        # 22 pinned dependencies
├── Dockerfile              # Multi-stage build (builder → runtime)
└── alembic.ini
```

### API Endpoints (21 total)

| Method | Path | Auth | Rate Limit | Description |
|--------|------|------|------------|-------------|
| GET | `/` | No | — | API info |
| GET | `/health` | No | — | Full healthcheck |
| GET | `/metrics` | API Key | — | Request metrics |
| GET | `/api/v1/auth/state` | No | 30/min | OAuth CSRF state token |
| POST | `/api/v1/auth/github/callback` | No | 10/min | GitHub OAuth callback |
| GET | `/api/v1/auth/me` | JWT | 30/min | Current user profile |
| POST | `/api/v1/auth/refresh` | JWT | — | Refresh JWT token |
| POST | `/api/v1/github/analyze/{username}` | JWT | 5/min | Build skill fingerprint |
| GET | `/api/v1/github/user/{username}` | No | 30/min | GitHub user proxy |
| GET | `/api/v1/github/fingerprint` | JWT | — | Get skill fingerprint |
| GET | `/api/v1/issues/matches` | JWT | 60/min | Personalized matches |
| POST | `/api/v1/issues/index` | JWT | 3/min | Trigger background indexing |
| POST | `/api/v1/issues/save/{id}` | JWT | 30/min | Save an issue |
| GET | `/api/v1/issues/saved` | JWT | 60/min | List saved issues |
| GET | `/api/v1/issues/trending` | No | 60/min | Trending issues |
| GET | `/api/v1/issues/smart-search` | Optional | 20/min | NLP search |
| GET | `/api/v1/issues/stats` | No | 60/min | Platform statistics |

---

## 3. Infrastructure & DevOps

### Docker (Local Development)

| Service | Image | Purpose |
|---------|-------|---------|
| `db` | pgvector/pgvector:pg16 | PostgreSQL 16 with pgvector extension |
| `redis` | redis:7-alpine | Caching, rate limiting, ARQ queue |
| `backend` | Custom (FastAPI) | API server (Gunicorn + Uvicorn) |
| `worker` | Custom (FastAPI) | ARQ background worker |
| `frontend` | Custom (Next.js) | SSR frontend |

### Render (Production)

| Service | Type | Plan |
|---------|------|------|
| `openissue-backend` | Web Service | Starter (Python 3.12) |
| `openissue-worker` | Background Worker | Starter (Python 3.12) |
| `openissue-frontend` | Web Service | Starter (Node 20) |

### CI/CD Pipeline (GitHub Actions)

7-job pipeline with full validation gates:

```
env-check
    ├── backend-lint (ruff + mypy)
    ├── frontend (npm ci + lint + typecheck + build)
    ├── backend-test (pytest with mocked DB)
    ├── db-validate (DNS → TCP → Auth → PgBouncer → Alembic → Schema → Runtime)
    │       │
    │       ▼
    │   startup-validate (boot FastAPI, hit /health)
    │   docker-validate  (build image, run container, hit /health)
    │       │
    │       ▼
    └── deploy (trigger Render deploy hook, main only)
```

### Database Schema (4 tables)

| Table | Columns | Indexes |
|-------|---------|---------|
| `users` | id, github_id, github_username, skill_json (JSONB), skill_vector (Vector128), ... | HNSW on skill_vector |
| `repositories` | id, github_id, full_name, stars, topics (JSON), ... | B-tree on full_name, stars |
| `issues` | id, github_id, number, title, skill_vector (Vector128), complexity_score, ... | HNSW on skill_vector |
| `saved_issues` | user_id, issue_id, status | Unique constraint on (user_id, issue_id) |

### AI Services

| Service | Model | Use Case | Cost Model |
|---------|-------|----------|------------|
| Groq | LLaMA 3.3 70B Versatile | Skill analysis, issue analysis, query parsing, match explanations | Free tier (30 RPM) |
| Jina | Embeddings v3 (128-dim) | Semantic vectorization for cosine similarity search | Free tier |

### Connection Pooling

| Config | Value | Strategy |
|--------|-------|----------|
| `DB_POOL_SIZE` | 20 (backend) / 0 (worker) | QueuePool (backend) / NullPool (worker) |
| `REDIS_MAX_CONNECTIONS` | 50 (backend) / 20 (worker) | Connection pool with retry |
| PgBouncer | Session mode compatible | `statement_cache_size=0` |

---

## 4. Security Features

| Feature | Implementation |
|---------|---------------|
| OAuth | GitHub OAuth via NextAuth v4 |
| JWT | HS256, 7-day expiry, HttpOnly cookie + Bearer token |
| CORS | Configurable origins, credentials enabled |
| Rate Limiting | SlowAPI (in-memory per-worker, 60/min default) |
| Security Headers | X-Content-Type-Options, X-Frame-Options, HSTS, Referrer-Policy |
| CSRF | Signed state tokens for OAuth flow |
| Input Validation | Pydantic v2 strict validation on all endpoints |
| Error Handling | Custom exception handlers (429, 500) with request ID tracking |
| Secrets | Environment variables, never committed |

---

## 5. Key Design Patterns

| Pattern | Where Used |
|---------|-----------|
| **Stale-while-revalidate** | Redis cache with probabilistic early expiry |
| **Request deduplication** | In-flight task tracking for concurrent identical requests |
| **Hybrid matching** | DB (pgvector) + live GitHub API results merged and re-ranked |
| **Graceful degradation** | Redis/AI/GitHub failures fall back to defaults |
| **Background persistence** | Fire-and-forget tasks for high-score issue storage |
| **Semaphore concurrency** | Bounded parallelism for AI calls (5) and GitHub fetches (4) |
| **Multi-stage Docker** | Builder stage (compile) → Runtime stage (slim) |
