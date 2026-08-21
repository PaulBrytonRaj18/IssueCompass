# IssueCompass — Project Status Report

> Generated: August 21, 2026
> Repository: [github.com/PaulBrytonRaj18/IssueCompass](https://github.com/PaulBrytonRaj18/IssueCompass)

---

## 1. What Is IssueCompass?

IssueCompass is an **AI-powered open-source issue matching platform** that helps developers find GitHub issues they can actually solve. It analyzes a developer's GitHub profile to build a skill fingerprint, then uses semantic vector search + AI scoring to match them with relevant open-source issues.

### Core Value Proposition

> "Stop browsing endless issue lists. Tell IssueCompass your skills, and it finds issues that match."

---

## 2. Current Features

### ✅ Built & Working

| Feature | Status | Description |
|---------|--------|-------------|
| GitHub OAuth Login | ✅ Complete | Sign in via GitHub, JWT session management |
| Skill Fingerprinting | ✅ Complete | Analyze GitHub repos → structured skill profile (languages, topics, experience level) |
| AI Skill Analysis | ✅ Complete | Groq LLM (LLaMA 3.3 70B) extracts skills from repo data |
| Vector Embeddings | ✅ Complete | Jina AI v3 generates 128-dim vectors for semantic matching |
| Personalized Matching | ✅ Complete | pgvector cosine similarity + hybrid scoring (12 dimensions) |
| Live GitHub Fallback | ✅ Complete | When DB results are sparse, fetches live from GitHub Search API |
| Trending Issues | ✅ Complete | Shows trending repos + their good-first-issues |
| Smart Search | ✅ Complete | Natural language search with AI query parsing |
| Save Issues | ✅ Complete | Bookmark issues for later |
| Background Indexing | ✅ Complete | ARQ worker indexes issues every 6 hours |
| Stale Issue Cleanup | ✅ Complete | Daily cron removes closed/stale issues |
| Rate Limiting | ✅ Complete | Per-user/IP rate limits via SlowAPI |
| Health Monitoring | ✅ Complete | /health endpoint (DB, Redis, pool status) |
| Structured Logging | ✅ Complete | JSON logging with request IDs |
| Error Tracking | ✅ Complete | Sentry integration (0.1% sample rate) |

### 🔄 Partially Built

| Feature | Status | Notes |
|---------|--------|-------|
| Search Page | ⚠️ Removed | Removed from frontend (`search/page.tsx` exists but routes to smart-search) |
| Skill Fingerprint Chart | ⚠️ Basic | Recharts radar chart for skill visualization |
| User Profile | ⚠️ Basic | Shows basic info, no edit functionality |

### ❌ Not Yet Built

| Feature | Description |
|---------|-------------|
| Issue Status Tracking | Track which saved issues the user is working on |
| Notification System | Email/webhook when new matching issues appear |
| Repository Follow | Follow repos to get notified of new issues |
| Team/Org Matching | Match issues for teams, not just individuals |
| Issue Difficulty Labels | Auto-classify issues as beginner/intermediate/advanced |
| Contribution Tracking | Track which issues the user has contributed to |
| Dark/Light Mode Toggle | ThemeProvider exists but no user-facing toggle |
| Mobile Responsive | Basic responsiveness, not optimized for mobile |
| Onboarding Flow | First-time user experience after OAuth |

---

## 3. Codebase Health

### Metrics

| Metric | Value |
|--------|-------|
| Backend source files | 25 (.py) |
| Backend LOC | 5,089 |
| Frontend source files | 26 (.tsx/.ts) |
| Frontend LOC | 3,019 |
| Test files | 12 |
| Test LOC | 2,791 |
| Test functions | 237 (backend pytest) |
| API endpoints | 21 |
| DB migrations | 4 revisions |
| npm dependencies | 16 (+ 15 dev) |
| Python dependencies | 22 |

### Code Quality

| Check | Status |
|-------|--------|
| Python linting (ruff) | ✅ Passing |
| TypeScript typecheck | ✅ Passing |
| Backend tests | ✅ 237 passing |
| Frontend tests | ⚠️ 3 tests only |
| Docker build | ✅ Multi-stage working |
| CI pipeline | ✅ 7-job pipeline |

### Test Coverage Gaps

| Module | Coverage |
|--------|----------|
| `routes/auth.py` | ✅ Well tested |
| `routes/issues.py` | ⚠️ Partial |
| `routes/github.py` | ⚠️ Partial |
| `services/ai_service.py` | ✅ 227 lines of tests |
| `services/matching_service.py` | ⚠️ Minimal (34 lines) |
| `services/search_service.py` | ✅ Good (103 lines) |
| `services/skill_service.py` | ⚠️ Minimal (57 lines) |
| `services/scoring_service.py` | ✅ Good (44 lines) |
| `services/github_service.py` | ✅ Good (135 lines) |
| `core/cache.py` | ✅ Extensive (463 lines) |
| `worker.py` | ✅ Good (165 lines) |
| Frontend components | ⚠️ Only EmptyState tested |

---

## 4. Architecture Summary

```
Browser → Next.js (SSR) → FastAPI (REST API) → PostgreSQL (pgvector)
                           │                       └── Redis (cache)
                           │
                           ├── GitHub REST API (repo/issue data)
                           ├── Groq Cloud (LLaMA 3.3 70B — skill analysis)
                           └── Jina AI (embeddings v3 — semantic vectors)
```

### Request Flow (Match Retrieval)

```
1. User loads /dashboard
2. NextAuth validates GitHub OAuth session
3. Frontend calls POST /api/v1/auth/github/callback → sync user in DB
4. Frontend calls GET /api/v1/issues/matches?limit=30
5. Backend runs concurrently:
   a. DB: pgvector cosine similarity search (local issues)
   b. GitHub: live search based on user's skill fingerprint
6. Results merged, deduplicated, re-ranked with 12-dimension scoring
7. High-score live issues persisted to DB (fire-and-forget)
8. Cached in Redis for 3 minutes
9. Returns scored matches with explanations
```

### Scoring Dimensions (12 factors)

| Weight | Dimension | Source |
|--------|-----------|--------|
| 0.50 | Skill match (cosine similarity) | pgvector / Jina embeddings |
| 0.15 | Popularity (stars, forks, comments) | GitHub API |
| 0.15 | Interest match (topic/category overlap) | Skill fingerprint |
| 0.10 | Repo activity (recent indexing, commit velocity) | GitHub API |
| 0.10 | Freshness (issue age) | GitHub API |

---

## 5. Bugs Found & Fixed (This Session)

### Critical Bugs

| Bug | Impact | Fix |
|-----|--------|-----|
| Docker port mismatch (`8000:8080`) | Backend unreachable from host | Changed to `8000:8000` |
| Missing `github_id` on live `Repository` objects | 500 errors on trending/smart-search | Added computed `github_id` |
| Missing `id` on live ORM objects | Pydantic ValidationError → 500 | Added `id=0` sentinel for live objects |
| Global failure counter never reset | Incorrect success/failure logging | Replaced with local counter |

### Code Quality Bugs

| Bug | Impact | Fix |
|-----|--------|-----|
| `INTEREST_DEFAULT` used before definition | Fragile code ordering | Moved to top with other constants |
| Duplicate `select` import in `dependencies.py` | Dead code | Removed redundant import |

### Dead Code Removed

| Item | File | Reason |
|------|------|--------|
| `_to_repo_public` redundant `isinstance` | `issues.py` | Both branches identical |
| `build_user_skills()` | `skill_service.py` | Never called |
| `generate_vector_text()` | `ai_service.py` | Never called (only in tests) |
| `SYSTEM_PROMPTS["vector_text"]` | `ai_service.py` | Only used by removed function |
| `generate_ai_explanation()` | `scoring_service.py` | Never called |
| `_jina_enabled()` | `ai_service.py` | Never called |
| `cache_health()` | `cache.py` | Only called in tests |
| `_persist_failure_count` global + helper | `matching_service.py` | Replaced with local variable |

**Net: 20 additions, 105 deletions across 9 files.**

---

## 6. Deployment Status

### Local Development (Docker Compose)

| Service | Port | Status |
|---------|------|--------|
| PostgreSQL + pgvector | 5432 | ✅ Configured |
| Redis | 6379 | ✅ Configured |
| Backend (FastAPI) | 8000 | ✅ Fixed (was broken) |
| Worker (ARQ) | — | ✅ Configured |
| Frontend (Next.js) | 3000 | ✅ Configured |

### Production (Render)

| Service | URL | Status |
|---------|-----|--------|
| Backend | openissue-backend.onrender.com | ✅ Deployed |
| Worker | — | ✅ Background service |
| Frontend | openissue-frontend.onrender.com | ✅ Deployed |

### CI/CD (GitHub Actions)

| Stage | Status |
|-------|--------|
| Env Validation | ✅ 9 required secrets |
| Backend Lint | ✅ ruff + mypy |
| Frontend Build | ✅ npm ci + lint + typecheck + build |
| Backend Tests | ✅ pytest with mocked DB |
| DB Validation | ✅ 7-step pipeline (DNS → PgBouncer → Alembic → Schema) |
| Startup Validation | ✅ Boot FastAPI → hit /health |
| Docker Validation | ✅ Build image → run container → hit /health |
| Deploy | ✅ Render deploy hook (main branch only) |

---

## 7. Environment Variables Required

| Variable | Required | Purpose |
|----------|----------|---------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `REDIS_URL` | ✅ | Redis connection string |
| `SECRET_KEY` | ✅ | JWT signing key |
| `GITHUB_TOKEN` | ✅ | GitHub API access (higher rate limits) |
| `OAUTH_GITHUB_CLIENT_ID` | ✅ | GitHub OAuth App |
| `OAUTH_GITHUB_CLIENT_SECRET` | ✅ | GitHub OAuth App |
| `GROQ_API_KEY` | ✅ | AI skill analysis (Groq Cloud) |
| `JINA_API_KEY` | ✅ | Vector embeddings (Jina AI) |
| `NEXTAUTH_SECRET` | ✅ | NextAuth JWT secret |
| `NEXTAUTH_URL` | ✅ | NextAuth base URL |
| `NEXT_PUBLIC_API_URL` | ✅ | Backend API URL for frontend |
| `AI_ENABLED` | Optional | Enable/disable Groq AI (default: true) |
| `EMBEDDINGS_ENABLED` | Optional | Enable/disable Jina embeddings (default: true) |
| `METRICS_API_KEY` | Optional | API key for /metrics endpoint |
| `SENTRY_DSN` | Optional | Sentry error tracking DSN |

---

## 8. Recommendations

### High Priority

1. **Add more frontend tests** — Only 3 test cases exist; component tests for Navbar, IssueCard, Dashboard would prevent regressions.
2. **Add integration tests** — Current tests mock everything; real DB + Redis integration tests would catch wiring bugs.
3. **Add request timeout middleware** — Long-running GitHub API calls can block; a timeout middleware would improve resilience.

### Medium Priority

4. **Implement notification system** — Users currently have no way to know when new matching issues appear.
5. **Add issue difficulty auto-classification** — The backend has scoring but no user-facing difficulty filter on the frontend.
6. **Improve error messages** — Generic "Internal server error" responses; could surface more detail in development mode.

### Low Priority

7. **Add dark mode toggle** — ThemeProvider exists but no UI control.
8. **Mobile responsiveness** — Currently desktop-focused.
9. **Add API documentation** — Swagger UI is at `/docs` but could be enhanced with examples.

---

## 9. File Structure Summary

```
IssueCompass/
├── .github/workflows/ci.yml    # 7-job CI/CD pipeline
├── docker-compose.yml           # 5 services (db, redis, backend, worker, frontend)
├── render.yaml                  # Render Blueprint (IaC)
├── nginx.conf                   # Reverse proxy config
├── ARCHITECTURE.md              # Architecture diagrams
├── CONTRIBUTING.md              # Contribution guidelines
├── backend/
│   ├── main.py                  # FastAPI entrypoint
│   ├── Dockerfile               # Multi-stage Python build
│   ├── requirements.txt         # 22 pinned dependencies
│   ├── app/                     # 25 source files (5,089 LOC)
│   │   ├── core/                # Infrastructure (config, DB, cache, auth)
│   │   ├── models/              # SQLAlchemy ORM (4 tables)
│   │   ├── schemas/             # Pydantic v2 models (18 schemas)
│   │   ├── routes/              # FastAPI routers (3 routers, 21 endpoints)
│   │   ├── services/            # Business logic (6 services)
│   │   └── worker.py            # ARQ background worker
│   ├── scripts/                 # CI/deployment helpers
│   ├── alembic/                 # DB migrations (4 revisions)
│   └── tests/                   # 237 test functions (2,791 LOC)
├── frontend/
│   ├── Dockerfile               # Node.js build
│   ├── package.json             # 16 + 15 dependencies
│   └── src/                     # 26 source files (3,019 LOC)
│       ├── app/                 # Next.js App Router (6 pages)
│       ├── components/          # 9 reusable components
│       ├── lib/                 # API layer, types, hooks
│       └── styles/              # Tailwind CSS globals
├── TECH_STACK_REPORT.md         # ← This file
└── PROJECT_STATUS_REPORT.md     # ← This file
```
