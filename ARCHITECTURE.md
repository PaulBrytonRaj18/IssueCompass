# IssueCompass — Architecture Diagram

```

                          ┌──────────────────────────────────────────────────────────────────────────┐

                          │                           USERS (Browser)                               │

                          │                                                                          │

                          │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │

                          │  │  Landing /   │  │  Dashboard   │  │   Search     │  │   Trending   │  │

                          │  │  page.tsx    │  │  page.tsx    │  │  page.tsx    │  │  page.tsx    │  │

                          │  └──────────────┘  └──────┬───────┘  └──────┬───────┘  └──────────────┘  │

                           │  ┌──────────────┐  ┌────────────────────────────┐                           │  │

                           │  │   Profile    │  │          Saved            │                           │  │

                           │  │  page.tsx    │  │        page.tsx           │                           │  │

                           │  └──────────────┘  └───────────────────────────┘                           │  │

                          └──────────────────────────────────────────────────────────────────────────┘

                                                    │

                                                    │ HTTPS / HTTP

                                                    ▼

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓

┃                              FRONTEND (Next.js 14 + React 18)                                     ┃

┃                                                                                                    ┃

┃  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐  ┃

┃  │                              next.config.js (SSR, Image opt)                                  │  ┃

┃  └──────────────────────────────────────────────────────────────────────────────────────────────┘  ┃

┃                                                                                                    ┃

┃  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐  ┃

┃  │                                   middleware.ts                                               │  ┃

┃  │  ┌────────────────────────────────────────────────────────────────────────────────────────┐  │  ┃

┃  │  │  protectedRoutes: /dashboard /profile /search /trending /saved                           │  │  ┃

┃  │  │  Auth check: ic_token cookie || next-auth.session-token → allow → else redirect /      │  │  ┃

┃  │  └────────────────────────────────────────────────────────────────────────────────────────┘  │  ┃

┃  └──────────────────────────────────────────────────────────────────────────────────────────────┘  ┃

┃                                                                                                    ┃

┃  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐  ┃

┃  │                         Client-Side Providers Stack (providers.tsx)                           │  ┃

┃  │  ErrorBoundary > ThemeProvider > QueryClientProvider > SessionProvider > ToastProvider        │  ┃

┃  └──────────────────────────────────────────────────────────────────────────────────────────────┘  ┃

┃                                                                                                    ┃

┃  ┌────────────────────────────────────────────────────────┐  ┌───────────────────────────────────┐  ┃

┃  │           REUSABLE COMPONENTS                          │  │           CUSTOM HOOKS            │  ┃

┃  │  ┌──────────┐ ┌──────────┐ ┌──────────────┐  ┌──────┐ │  │  ┌─────────────────┐ ┌──────────┐ │  ┃

┃  │  │  Navbar   │ │IssueCard│ │  EmptyState   │  │Toast │ │  │  │ use-auth.ts     │ │use-issues│ │  ┃

┃  │  └──────────┘ └──────────┘ └──────────────┘  └──────┘ │  │  │ syncUser        │ │ .ts      │ │  ┃

┃  │  ┌──────────┐ ┌──────────┐ ┌──────────────┐  ┌──────┐ │  │  └─────────────────┘ └──────────┘ │  ┃

┃  │  │Spinner   │ │Skeleton  │ │ErrorBoundary │  │Theme │ │  │  ┌─────────────────┐ ┌──────────┐ │  ┃

┃  │  │ .tsx     │ │Card.tsx  │ │ .tsx         │  │Prov  │ │  │  │ use-github.ts   │ │use-search│ │  ┃

┃  │  └──────────┘ └──────────┘ └──────────────┘  └──────┘ │  │  │ fingerprint     │ │s .ts     │ │  ┃

┃  │  ┌──────────────────┐                                 │  │  │ analyzeProfile  │ └──────────┘ │  ┃

┃  │  │ SkillFingerprint  │                                 │  │  └─────────────────┘              │  ┃

┃  │  │ .tsx (Recharts)   │                                 │  │  ┌──────────────────┐             │  ┃

┃  │  └──────────────────┘                                 │  │                                   │  ┃

┃  └────────────────────────────────────────────────────────┘  │                                   │  ┃

┃                                                               └───────────────────────────────────┘  ┃

┃                                                                                                    ┃

┃  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐  ┃

┃  │                          API Layer (api.ts — axios instance)                                 │  ┃

┃  │  ┌──────────────────────────────────────────────────────────────────────────────────────┐    │  ┃

┃  │  │  interceptors: request (Bearer token) / response (401→refresh, 429→message, 5xx→retry)│    │  ┃

┃  │  │  authApi: callback, getMe, refresh │ githubApi: analyze, fingerprint, user             │    │  ┃

  ┃  │  │  issuesApi: matches, search, smartSearch, trending, saved, save, index, stats          │    │  ┃

┃  │  └──────────────────────────────────────────────────────────────────────────────────────┘    │  ┃

┃  └──────────────────────────────────────────────────────────────────────────────────────────────┘  ┃

┃                                                                                                    ┃

┃  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐  ┃

┃  │  Styles: Tailwind CSS + globals.css (custom vars, keyframes, prefers-reduced-motion)          │  ┃

  ┃  │  Types: types.ts (User, Issue, MatchedIssue, Repo, LANGUAGE_COLORS)                           │  ┃

┃  │  Auth: NextAuth v4 + GitHub OAuth provider + JWT session strategy + backend JWT sync          │  ┃

┃  └──────────────────────────────────────────────────────────────────────────────────────────────┘  ┃

┃                                                                                                    ┃

┃  ┌──────────────────────────────────────────────────────────┐                                     ┃

┃  │  NextAuth → GitHub OAuth flow:                           │                                     ┃

┃  │  1. User clicks "Sign in" → GitHub OAuth consent screen  │                                     ┃

┃  │  2. GitHub redirects to /api/auth/callback/github        │                                     ┃

┃  │  3. NextAuth JWT callback stores githubId, username, etc │                                     ┃

┃  │  4. Frontend calls POST /api/v1/auth/github/callback     │                                     ┃

┃  │     to create JWT in backend and store in sessionStorage  │                                     ┃

┃  └──────────────────────────────────────────────────────────┘                                     ┃

┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

                          │

                          │ HTTP (port 3000 → mapped to 8080 inside container)

                          ▼

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓

┃                              NGINX REVERSE PROXY (optional, single-container deployment)          ┃

┃                                                                                                    ┃

┃  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐  ┃

┃  │  /api/v1/*   ──→  proxy_pass http://127.0.0.1:8000  (backend FastAPI)                        │  ┃

┃  │  /health     ──→  proxy_pass http://backend          (backend)                                │  ┃

┃  │  /docs       ──→  proxy_pass http://backend          (Swagger UI)                             │  ┃

┃  │  /openapi.json ──→ proxy_pass http://backend         (OpenAPI spec)                           │  ┃

┃  │  /*          ──→  proxy_pass http://frontend:3000    (Next.js SSR)                            │  ┃

┃  └──────────────────────────────────────────────────────────────────────────────────────────────┘  ┃

┃                                                                                                    ┃

┃  Security headers: X-Content-Type-Options, X-Frame-Options(DENY), HSTS, Referrer-Policy, etc.     ┃

┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

                          │

                          │ HTTP (port 8000)

                          ▼

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓

┃                          BACKEND (Python 3.12 — FastAPI + Gunicorn)                               ┃

┃                                                                                                    ┃

┃  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐  ┃

┃  │  main.py — Application Entrypoint                                                             │  ┃

┃  │  Lifespan:  settings.check_errors() → init_redis() → yield → close_db() → close_ai() → ...    │  ┃

┃  │  Middleware: CORS + GZip + Security Headers                                                    │  ┃

┃  │  Exception handlers: RateLimitExceeded(429), generic Exception(500)                            │  ┃

┃  │  Sentry: 0.1% traces, 0.1% profiles (if SENTRY_DSN set)                                       │  ┃

┃  └──────────────────────────────────────────────────────────────────────────────────────────────┘  ┃

┃                                                                                                    ┃

┃  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐  ┃

  ┃  │  ROUTES (all under /api/v1) — 14 endpoints total                                              │  ┃

┃  │                                                                                                │  ┃

┃  │  ┌─ auth.py ────────────────────────┐  ┌─ github.py ──────────────────────────────────────┐   │  ┃

┃  │  │ GET  /auth/state     (30/min)    │  │ POST /github/analyze/{username}   (5/min)       │   │  ┃

┃  │  │ POST /auth/github/cb  (10/min)   │  │ GET  /github/user/{username}     (30/min)       │   │  ┃

┃  │  │ GET  /auth/me        (30/min)    │  │ GET  /github/fingerprint                        │   │  ┃

┃  │  │ POST /auth/refresh               │  └─────────────────────────────────────────────────┘   │  ┃

┃  │  └──────────────────────────────────┘                                                       │  ┃

┃  │  ┌─ issues.py ──────────────────────────────────────────────────────────────────────────┐   │  ┃

┃  │  │ GET  /issues/matches             │ POST  /issues/save/{id}      (30/min)              │   │  ┃

┃  │  │ POST /issues/index     (3/min)   │ GET   /issues/saved                                │   │  ┃

┃  │  │ GET  /issues/search   (30/min)   │ GET   /issues/trending                             │   │  ┃

┃  │  │ GET  /issues/smart-search(20/min)│ GET   /issues/stats                                │   │  ┃

┃  │  └───────────────────────────────────────────────────────────────────────────────────────┘   │  ┃

┃  │                                                                                              │  ┃

┃  │  Direct (not in routers):                                                                     │  ┃

┃  │  GET  /   (root info)                                                                         │  ┃

┃  │  GET  /health (full healthcheck)                                                               │  ┃

┃  │  GET  /metrics (X-Metrics-Key auth)                                                            │  ┃

┃  └──────────────────────────────────────────────────────────────────────────────────────────────┘  ┃

┃                                                                                                    ┃

┃  ┌────────────────────────────────────────────────────────┐  ┌───────────────────────────────────┐ ┃

┃  │  CORE MODULES                                         │  │  SERVICES                         │ ┃

┃  │                                                       │  │                                   │ ┃

┃  │  config.py     — Pydantic Settings from env vars      │  │  ai_service.py   (450 lines)      │ ┃

┃  │  database.py   — Async SQLAlchemy + PgBouncer pool    │  │    └─ Groq LLM (llama-3.3-70b)   │ ┃

┃  │  cache.py      — Redis + probabilistic early expiry   │  │    └─ Jina AI Embeddings (v3)    │ ┃

┃  │  dependencies.py— JWT auth dependency injection       │  │    └─ Semaphore(5), cached, dedup │ ┃

┃  │  monitoring.py — Request logging + metrics (deque)    │  │                                   │ ┃

┃  │  ratelimit.py  — SlowAPI config (Redis/in-memory)     │  │  github_service.py (370 lines)    │ ┃

┃  │  utils.py      — DateTime parsing utility             │  │    └─ httpx client (reused,cached)│ ┃

┃  │                                                       │  │    └─ Rate-limit throttle         │ ┃

┃  │  models/                                             │  │    └─ fetch_user, search, issues  │ ┃

┃  │    models.py   — SQLAlchemy ORM (4 tables)            │  │                                   │ ┃

┃  │    └─ User (skill_json, skill_vector[128])             │  │  matching_service.py (621 lines)  │ ┃

┃  │    └─ Repository (pgvector enabled)                   │  │    └─ Vector similarity search    │ ┃

┃  │    └─ Issue (skill_vector[128], complexity_score)      │  │    └─ Live GitHub fallback       │ ┃

┃  │    └─ SavedIssue (user_id FK, issue_id FK)            │  │    └─ Hybrid scoring + re-ranking│ ┃

┃  │                                                       │  │                                   │ ┃

┃  │  schemas/                                            │  │  scoring_service.py (429 lines)    │ ┃

┃  │    schemas.py — 18 Pydantic v2 models                 │  │    └─ SCORE_WEIGHTS (12 constants)│ ┃

┃  │                                                       │  │    └─ compute_freshness           │ ┃

┃  │  migrations/ (Alembic — 4 revisions)                  │  │    └─ compute_popularity          │ ┃

┃  │    └─ 0001_initial, 0002_nullable,                    │  │    └─ compute_interest_match      │ ┃

┃  │    └─ 0003_skill_json, 0004_hnsw_vector_indexes       │  │    └─ score_live_issue            │ ┃

┃  │                                                       │  │                                   │ ┃

┃  └───────────────────────────────────────────────────────┘  │  skill_service.py (402 lines)     │ ┃

┃                                                              │    └─ build_skill_fingerprint     │ ┃

┃                                                              │    └─ SKILL_CATEGORIES (AI+regex)│ ┃

┃                                                              │    └─ compute_complexity          │ ┃

┃                                                              │    └─ extract_required_skills     │ ┃

┃                                                              │    └─ hash-based vectorizer        │ ┃

┃                                                              │                                   │ ┃

┃                                                              │  search_service.py (519 lines)    │ ┃

┃                                                              │    └─ parse_natural_query (AI/rule)│ ┃

┃                                                              │    └─ smart_search (hybrid)        │ ┃

┃                                                              │    └─ keyword relevance scoring   │ ┃

┃                                                              └───────────────────────────────────┘ ┃

┃                                                                                                    ┃

┃  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐  ┃

┃  │  WORKER (ARQ — async background job queue, connected via Redis)                              │  ┃

┃  │                                                                                              │  ┃

┃  │  Cron Jobs:                                                                                  │  ┃

┃  │    index_issues_task         — Every 6h (0,6,12,18 UTC) top 12 user languages × 2 labels    │  ┃

┃  │    cleanup_stale_issues_task — Daily 3:30 UTC → DELETEs closed/30d-old issues               │  ┃

┃  │                                                                                              │  ┃

┃  │  Ad-hoc Functions:                                                                           │  ┃

┃  │    full_index(languages)     — Index all configured languages × GFI+HW labels (parallel 3)   │  ┃

┃  │    index_language_issues     — Fetch from GitHub API → create repos/issues → embeddings      │  ┃

┃  └──────────────────────────────────────────────────────────────────────────────────────────────┘  ┃

┃                                                                                                    ┃

┃  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐  ┃

┃  │  SCRIPTS (CI / Deployment helpers)                                                           │  ┃

┃  │  db_reconcile.py  — Pre-migration schema check (NullPool, NO_PGBOUNCER check)                │  ┃

┃  │  ci_validate.py   — Pre-deployment validation suite (DB, Redis, API, AI, OAuth)              │  ┃

┃  │  ci_db_check.py   — CI database health + migration head check (_EXPECTED_HEAD="0004")         │  ┃

┃  └──────────────────────────────────────────────────────────────────────────────────────────────┘  ┃

┃                                                                                                    ┃

┃  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐  ┃

┃  │  TESTS (backend/tests/)                                                                      │  ┃

┃  │  test_routes.py        (418 lines)  conftest.py       (144 lines)  test_cache.py (463 lines) │  ┃

┃  │  test_scoring_service  (44 lines)  test_ai_service    (227 lines)  test_edge_cases(377 lines)│  ┃

┃  │  test_github_service   (135 lines) test_skill_service  (57 lines)  test_worker(165 lines)    │  ┃

┃  │  test_matching_service (34 lines)  test_search_service (103 lines)                           │  ┃

┃  └──────────────────────────────────────────────────────────────────────────────────────────────┘  ┃

┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

                          │                              │

                          │ TCP (5432)                    │ TCP (6379)

                          ▼                              ▼

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓

┃  POSTGRESQL 16 (pgvector/pgvector)        ┃    ┃  REDIS 7 (Cache + Rate Limit + ARQ)     ┃

┃                                           ┃    ┃                                          ┃

┃  ┌─────────────────────────────────────┐  ┃    ┃  ┌──────────────────────────────────┐   ┃

┃  │  users                              │  ┃    ┃  │  Cache keys:                     │   ┃

┃  │  ├─ id (PK)                         │  ┃    ┃  │  └─ ai:{md5}:{text}              │   ┃

┃  │  ├─ github_id (UQ, idx)             │  ┃    ┃  │  └─ gh:{endpoint}                │   ┃

┃  │  ├─ skill_json (JSONB)              │  ┃    ┃  │  └─ auth:me:{id}                 │   ┃

┃  │  └─ skill_vector(Vector128)         │  ┃    ┃  │  └─ matches:{hash}               │   ┃

┃  ├─────────────────────────────────────┤  ┃    ┃  │  └─ trending:{lang}               │   ┃

┃  │  repositories                       │  ┃    ┃  │  └─ search:{query}               │   ┃

┃  │  ├─ id (PK)                         │  ┃    ┃  │  └─ platform_stats               │   ┃

┃  │  ├─ github_id (UQ, idx)             │  ┃    ┃  ├──────────────────────────────────┤   ┃

┃  │  ├─ full_name (UQ, idx)             │  ┃    ┃  │  Rate limit keys                 │   ┃

┃  │  ├─ stars (idx)                     │  ┃    ┃  │  ARQ job queue                   │   ┃

┃  │  └─ topics (JSON)                   │  ┃    ┃  │  Probabilistic early expiry      │   ┃

┃  ├─────────────────────────────────────┤  ┃    ┃  └──────────────────────────────────┘   ┃

┃  │  issues                             │  ┃    ┃                                          ┃

┃  │  ├─ id (PK)                         │  ┃    ┃  Config: MAX_CONNECTIONS=50              ┃

┃  │  ├─ github_id (UQ, idx)             │  ┃    ┃  SOCKET_TIMEOUT=5s                       ┃

┃  │  ├─ repository_id (FK, idx)         │  ┃    ┃                                          ┃

┃  │  ├─ skill_vector(Vector128)        │  ┃    ┃                                          ┃

┃  │  ├─ required_skills (JSON)          │  ┃    ┃                                          ┃

┃  │  ├─ complexity_score(Float)         │  ┃    ┃                                          ┃

┃  │  ├─ is_good_first_issue (idx)       │  ┃    ┃                                          ┃

┃  │  └─ is_help_wanted (idx)            │  ┃    ┃                                          ┃

┃  ├─────────────────────────────────────┤  ┃    ┃                                          ┃

┃  │  saved_issues                       │  ┃    ┃                                          ┃

┃  │  ├─ user_id (FK, idx)               │  ┃    ┃                                          ┃

┃  │  ├─ issue_id (FK, idx)              │  ┃    ┃                                          ┃

┃  │  └─ UQ(user_id, issue_id)           │  ┃    ┃                                          ┃

┃  │  └─ notify / last_checked_at        │  ┃    ┃                                          ┃

┃  └─────────────────────────────────────┘  ┃    ┃                                          ┃

┃                                           ┃    ┃                                          ┃

┃  Indexes:                                 ┃    ┃                                          ┃

┃  └─ HNSW on skill_vector (cosine)        ┃    ┃                                          ┃

┃     for fast approximate search           ┃    ┃                                          ┃

┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛    ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

                          │                                      │

                          │                                      │

                          ▼                                      ▼

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓

┃                                    EXTERNAL API DEPENDENCIES                                      ┃

┃                                                                                                    ┃

┃  ┌──────────────────────────┐  ┌──────────────────────────┐  ┌───────────────────────────────────┐┃

┃  │   GitHub REST API v3     │  │   Groq Cloud AI          │  │   Jina AI Embeddings API          │┃

┃  │   api.github.com         │  │   api.groq.com           │  │   api.jina.ai                     │┃

┃  │                          │  │                          │  │                                   │┃

┃  │  Used by:                │  │  Used by:                │  │  Used by:                          │┃

┃  │  └─ github_service.py   │  │  └─ ai_service.py        │  │  └─ ai_service.py                 │┃

┃  │  └─ fetch_user repos    │  │  └─ parse_natural_query  │  │  └─ issue_text_to_vector          │┃

┃  │  └─ search issues       │  │  └─ build_skill_fp       │  │  └─ skill_fp_to_vector            │┃

┃  │  └─ live issue fetches  │  │  └─ extract_skills       │  │  └─ retry(2), cached(1h)          │┃

┃  │  └─ cached(1h)          │  │  └─ cached(1h), dedup    │  └───────────────────────────────────┘┃

┃  └──────────────────────────┘  └──────────────────────────┘                                       ┃

┃                                                                                                    ┃

┃  ┌──────────────────────────┐  ┌────────────────────────────────────────────────────────────────┐  ┃

┃  │   GitHub OAuth App       │  │   Render Cloud (Production Deployment)                         │  ┃

┃  │                          │  │                                                                  │  ┃

┃  │  ┌─ Client ID           │  │  ┌─ Backend Web Service (Gunicorn + Uvicorn)                   │  ┃

┃  │  └─ Client Secret       │  │  │  start: db_reconcile → alembic upgrade → gunicorn main:app  │  ┃

┃  │                          │  │  └─ healthcheck: GET /health                                   │  ┃

┃  │  Used by:                │  │                                                                  │  ┃

┃  │  └─ NextAuth provider   │  │  ┌─ Frontend Static Site (Next.js standalone output)            │  ┃

┃  │  └─ backend /auth/cb   │  │  └─ Node server.js on ${PORT:-8080}                              │  ┃

┃  └──────────────────────────┘  └────────────────────────────────────────────────────────────────┘  ┃

┃                                                                                                    ┃

┃  ┌──────────────────────────────────────────────────────────────────────────────────────────────┐  ┃

┃  │  CI/CD Pipeline (GitHub Actions — .github/workflows/ci.yml)                                 │  ┃

┃  │                                                                                              │  ┃

┃  │  1. env-check ── 9 required secrets validated                                                │  ┃

┃  │  2. pylint ─── ruff check . (E, F, I, N, W) + mypy backend/app/                             │  ┃

┃  │  3. test ─── pytest (asyncio_mode=auto, 15 test files) on Python 3.12 + Node 24             │  ┃

┃  │  4. docker-validate ── build backend Dockerfile (CI only)                                   │  ┃

┃  │  5. deploy ── curl Render deploy hook (main branch only)                                    │  ┃

┃  └──────────────────────────────────────────────────────────────────────────────────────────────┘  ┃

┃                                                                                                    ┃

┃  Pre-commit: ruff check + ruff format + mypy + check-yaml + end-of-file-fixer + trailing-whitespace┃

┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

╔═══════════════════════════════════════════════════════════════════════════════════════════════════╗

║                              DATA FLOW — REQUEST LIFECYCLE                                       ║

║                                                                                                   ║

║  ┌──────────┐    ┌──────────┐    ┌───────────┐    ┌──────────────┐    ┌──────────────┐          ║

║  │ Browser  │───▶│ NextAuth │───▶│  Next.js  │───▶│   FastAPI    │───▶│   Service    │          ║

║  │ (React)  │    │ (JWT)    │    │  (SSR)    │    │  (REST API)  │    │   Layer      │          ║

║  └──────────┘    └──────────┘    └───────────┘    └──────┬───────┘    └──────┬───────┘          ║

║                                                          │                  │                    ║

║                     Example: User loads Dashboard        │                  │                    ║

║                                                          ▼                  ▼                    ║

║  1. Browser GET /dashboard ────────────────→ Next.js renders page                                ║

║  2. Client: check session ────────────────→ useSession() → NextAuth JWT                          ║

║  3. Client: sync user ────────────────────→ POST /api/v1/auth/github/callback                    ║

║                                              └─→ dependencies.get_current_user → verify JWT     ║

║                                              └─→ routes/auth.github_callback → upsert User      ║

║                                              └─→ return JWT                                      ║

║  4. Client: fetch matches ────────────────→ GET /api/v1/issues/matches                           ║

║                                              └─→ dependencies.get_current_user → decode JWT     ║

║                                              └─→ matching_service.get_matched_issues()           ║

║                                                   ├─ Check cache → miss                         ║

║                                                   ├─ Get user skill_vector from DB              ║

║                                                   ├─ Cosine similarity search (HNSW) in DB      ║

║                                                   ├─ Score results (freshness + popularity)      ║

║                                                   ├─ Fall back to GitHub API if sparse           ║

║                                                   ├─ Re-rank + personalize (interest match)     ║

║                                                   ├─ Persist high-score issues (fire-and-forget) ║

║                                                   └─ Cache for 180s + return                    ║

║  5. Client: render IssueCards ←─────── JSON ←───────┘                                            ║

║                                                                                                   ║

╚═══════════════════════════════════════════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════════════════════════════════════════════╗

║                               SKILL FINGERPRINT PIPELINE                                          ║

║                                                                                                    ║

║  POST /api/v1/github/analyze/{username}                                                            ║

║                                                                                                    ║

║  ┌──────────┐   ┌──────────────────┐   ┌─────────────────┐   ┌──────────────────┐                ║

║  │ Fetch    │──▶│ Build Fingerprint│──▶│ Merge AI + Regex│──▶│ Vectorize &      │                ║

║  │ GitHub   │   │                  │   │                 │   │ Store in DB      │                ║

║  │ Repos    │   │ 1. Try AI (Groq) │   │ _merge_ai_fp() │   │                  │                ║

║  │ (cached) │   │ 2. Fallback regex│   │ → categories   │   │ skill_vector[128]│                ║

║  └──────────┘   │ 3. Experience lvl │   │ → top_skills   │   │ → pgvector HNSW  │                ║

║                  │ 4. Languages +    │   │ → experience   │   │                  │                ║

║                  │    topics + repos │   │ → topics       │   │ skill_json (JSONB)│               ║

║                  └──────────────────┘   └─────────────────┘   └──────────────────┘                ║

╚════════════════════════════════════════════════════════════════════════════════════════════════════╝

## Key Architecture Facts

| Component | Stack | Key Detail |

|-----------|-------|------------|

| **Frontend** | Next.js 14 + React 18 + TypeScript | SSR pages, client-side auth, TanStack Query caching |

| **Backend** | Python 3.12 + FastAPI + Gunicorn | 21 REST endpoints, Rate-limited (SlowAPI), CORS |

| **Database** | PostgreSQL 16 + pgvector | HNSW index on 128-dim vectors for cosine similarity |

| **Cache** | Redis 7 | Probabilistic early expiry, deduplication, ARQ queue |

| **AI** | Groq (LLaMA 3.3 70B) + Jina Embeddings v3 | Skill fingerprinting + natural language search |

| **Orchestration** | Docker Compose (local) / Render (prod) | 4 services (db, redis, backend, frontend) |

| **Auth** | NextAuth v4 (GitHub OAuth) + Backend JWT | Dual auth: HttpOnly cookie + Bearer token |

| **Worker** | ARQ (async job queue) | Cron: index every 6h, cleanup daily at 3:30 UTC |

## Service Dependency Graph

```

Browser  ──→  Frontend (Next.js)  ──→  Backend (FastAPI)  ──→  PostgreSQL

                │                                             └──→  Redis

                │                                                    │

                └──  NextAuth (GitHub OAuth)                        └──  ARQ Worker ──→ Backend

                                                                                          │

                                                                               GitHub API ←┘

                Backend  ──→  Groq AI API

                Backend  ──→  Jina AI API

```

## End-to-End Data Flow (Match Retrieval)

```

Browser → router.push /dashboard

         → middleware.ts checks auth (cookie or token)

         → layout.tsx renders <Providers> → <Toast>, <Navbar>

         → DashboardPage mounts

              → useSession() → "authenticated"

              → useEffect: syncMutation (POST /auth/github/callback)

              → syncMutation.isSuccess → useMatches enabled

                   → GET /api/v1/issues/matches?limit=30

                        → FastAPI: get_current_user (JWT decode)

                        → matching_service.get_matched_issues

                             → cache_get → miss

                             → DB: fetch user.skill_vector

                             → DB: HNSW cosine similarity search

                             → scoring_service: score each match

                             → if < 5 results: GitHub API fallback

                             → re_rank_results

                             → cache_set (180s TTL)

                   ← JSON: { matches: [...], user_skills: {...} }

              → render IssueCard[] with match_score bars, why_matched, skills

```
