# IssueCompass — Complete System Analysis

> **Match open-source contributors to issues they can actually solve.**

---

## Table of Contents

1. [Core Idea & Vision](#1-core-idea--vision)
2. [System Architecture](#2-system-architecture)
3. [Data Model](#3-data-model)
4. [API Layer (Routes)](#4-api-layer-routes)
5. [Service Layer (Core Logic)](#5-service-layer-core-logic)
6. [AI/ML Pipeline](#6-aiml-pipeline)
7. [Database Layer](#7-database-layer)
8. [Caching & Redis](#8-caching--redis)
9. [Infrastructure & Deployment](#9-infrastructure--deployment)
10. [Testing Strategy](#10-testing-strategy)
11. [Security Architecture](#11-security-architecture)
12. [Observability](#12-observability)
13. [Appendix: File Map](#13-appendix-file-map)

---

## 1. Core Idea & Vision

### Problem

Open-source contribution suffers from a **discovery gap**:

- **Contributors** spend hours browsing GitHub aimlessly, unable to find issues that match their skill set
- **Maintainers** tag issues as "good first issue" but attract contributors without the right skills
- **Existing tools** (GitHub Explore, goodfirstissue.dev) are generic lists with zero personalization

### Solution

IssueCompass bridges this gap by building a **personal skill fingerprint** from a developer's actual GitHub activity — their repos, languages, stars, topics, and contributions — then using **semantic vector similarity search** (pgvector) to match them with open issues across thousands of indexed repositories.

### Core Loop

```
GitHub Login → Fetch repos & activity data
                         ↓
              Build skill fingerprint (AI or regex)
                         ↓
              Convert to 128-dim vector (AI embed or hash)
                         ↓
              Semantic cosine similarity vs issue vectors
                         ↓
              Personalized, scored recommendation feed
```

### Three User Personas

1. **Contributors** — discover issues they can actually solve, filtered by skill match, difficulty, language, and interests
2. **Maintainers** — dashboard showing repo health metrics, and contributor discovery for their issues
3. **Anonymous** — basic keyword search and trending issues without authentication

---

## 2. System Architecture

### High-Level Topology

```
┌───────────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js 14)                         │
│  Landing · Dashboard · Search · Trending · Saved · Maintainer Views  │
│  NextAuth (GitHub OAuth) · TanStack Query · Tailwind · Framer Motion │
└───────────────────────────┬───────────────────────────────────────────┘
                            │ HTTP/JSON (port 8080 → Nginx)
                            ▼
┌───────────────────────────────────────────────────────────────────────┐
│                     Nginx Reverse Proxy                               │
│  Routes: /api/v1/* → backend (port 8000)                              │
│          / → frontend (port 3000)                                     │
│          /health → backend                                            │
└───────────────────────┬───────────────────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Uvicorn)                           │
│                                                                       │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌────────────────────┐   │
│  │ Auth     │  │ Issues   │  │ Search    │  │ Maintainer         │   │
│  │ (JWT)    │  │ (Matches)│  │ (NL→SQL)  │  │ Dashboard          │   │
│  └──────────┘  └──────────┘  └───────────┘  └────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    Core Services                                │  │
│  │  GitHub API · Skill Analysis · Matching Engine · Scoring Engine │  │
│  │  AI Service (Groq LLM) · Search Parser (NL→Intent)             │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└───────────────────┬──────────────────────────────────────┬─────────────┘
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
         │  • Saved searches│                  │                  │
         └──────────────────┘                  └──────────────────┘
```

### Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Framework** | FastAPI | 0.111.0 | Async Python web framework with OpenAPI docs |
| **ORM** | SQLAlchemy | 2.0.30 | Async PostgreSQL access with `AsyncSession` |
| **Driver** | asyncpg | 0.29.0 | High-performance async PostgreSQL driver |
| **Database** | PostgreSQL 16 + pgvector | 0.3.2 | Relational data + 128-dim vector similarity search |
| **Migrations** | Alembic | 1.13.1 | Schema versioning (3 migrations) |
| **Cache** | Redis (Upstash) | 7.x | API caching, rate limiting, ARQ job broker |
| **AI (Text)** | Groq (Llama 3.3 70B) | — | Skill extraction, NL query parsing, match explanations |
| **AI (Embeddings)** | Jina AI (v3) | — | Text-to-vector embedding generation |
| **Auth** | JWT (HS256) + NextAuth | — | Stateless API auth, GitHub OAuth |
| **Worker** | ARQ | 0.26.0 | Redis-backed async background jobs |
| **HTTP Client** | httpx | 0.27.0 | GitHub REST API with connection pooling |
| **Rate Limiting** | slowapi | 0.1.9 | Per-user/per-IP request throttling |
| **Web Server** | Gunicorn + Uvicorn | 22+0.29 | Production ASGI serving with worker processes |
| **Reverse Proxy** | Nginx | — | Unified port, path-based routing |
| **Frontend** | Next.js | 14.2.3 | React SSR with Tailwind CSS |
| **Container** | Docker + Compose | — | Multi-stage build, 4 service orchestration |

---

## 3. Data Model

### Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────────┐
│    User      │       │   Repository     │       │     Issue        │
├──────────────┤       ├──────────────────┤       ├──────────────────┤
│ id (PK)      │       │ id (PK)          │       │ id (PK)          │
│ github_id (UQ)│◄──────│ github_id (UQ)   │       │ github_id (UQ)   │
│ github_username│     │ full_name (UQ)   │       │ number           │
│ github_avatar │       │ name             │       │ title            │
│ github_name   │       │ description      │       │ body (Text)      │
│ github_bio    │       │ owner_login      │       │ html_url         │
│ email         │       │ html_url         │       │ state            │
│ public_repos  │       │ stars            │──┐    │ labels (JSON)    │
│ followers     │       │ forks            │  │    │ is_good_first_issue│
│ skill_json (JSON)│    │ primary_language │  │    │ is_help_wanted   │
│ skill_vector (VEC)│   │ topics (JSON)    │  │    │ required_skills(JSON)│
│ skill_last_upd │      │ is_archived      │  │    │ skill_vector(VEC)│
│ created_at     │      │ last_indexed     │  │    │ complexity_score │
│ last_login     │      └──────────────────┘  │    │ comments         │
└───────┬───────┘                             │    │ author_login     │
        │                                     │    │ created_at       │
        │  ┌────────────────────────┐         │    │ updated_at       │
        ├──│     SavedIssue         │         │    │ repository_id(FK)│◄──┘
        │  ├────────────────────────┤         │    └──────────────────┘
        │  │ id (PK)                │         │
        │  │ user_id (FK → User)    │         │
        │  │ issue_id (FK → Issue)  │─────────┘
        │  │ saved_at               │
        │  │ status                 │
        │  │ UNIQUE(user_id,issue_id)│
        │  └────────────────────────┘
        │
        │  ┌────────────────────────┐
        └──│     SavedSearch        │
           ├────────────────────────┤
           │ id (PK)                │
           │ user_id (FK → User)    │
           │ name                   │
           │ query                  │
           │ filters (JSON)         │
           │ notify                 │
           │ created_at             │
           │ last_checked_at        │
           └────────────────────────┘
```

### Table Schemas

**User (`users`):**
- `github_id` (BigInt, unique) — GitHub's user ID
- `skill_json` (JSON) — structured skill fingerprint: `{languages: {}, topics: [], categories: {}, experience_level: str, top_skills: []}`
- `skill_vector` (Vector(128)) — pgvector embedding for semantic similarity search
- `skill_last_updated` (timestamptz) — when the fingerprint was last computed

**Repository (`repositories`):**
- `github_id` (BigInt, unique) — GitHub's repo ID
- `full_name` (str, unique) — e.g., `facebook/react`
- `stars`, `forks` — popularity metrics used in scoring
- `is_archived` (bool) — archived repos get zero activity score
- `last_indexed` (timestamptz) — freshness metric for scoring

**Issue (`issues`):**
- `github_id` (BigInt, unique) — GitHub's issue ID
- `labels` (JSON) — e.g., `["bug", "good first issue"]`
- `required_skills` (JSON) — AI-extracted: `{skills: [], categories: {}, complexity: 0.0-1.0, effort: str, issue_type: str}`
- `skill_vector` (Vector(128)) — pgvector embedding for semantic matching
- `complexity_score` (Float, 0-1) — how difficult the issue is
- Foreign key to `repositories.id`

**Indexes:**
- Partial composite index: `ix_issues_state_vector` on `(state, skill_vector) WHERE skill_vector IS NOT NULL`
- Single-column: language, stars, owner_login, updated_at, state, repo_id, GFI, HW flags
- Full-text (via ILIKE): title, body for keyword search

### Migration Chain

1. **0001** — Initial schema: `users`, `repositories`, `issues`, `saved_issues`
2. **0002** — Performance indexes: composite state+repo, updated_at, state+vector partial, language, notify
3. **0003** — Creates missing `saved_searches` table, fixes `ix_issues_state_vector` to include `skill_vector` column

**Migration safety:** `scripts/db_reconcile.py` detects when tables exist but `alembic_version` is missing (e.g., from pre-Alembic schema creation), and stamps the head to prevent `DuplicateTableError`.

---

## 4. API Layer (Routes)

All routes are mounted under `/api/v1`.

### Auth Routes (`app/routes/auth.py`)

| Method | Path | Auth | Rate Limit | Cache | Description |
|--------|------|------|------------|-------|-------------|
| GET | `/auth/state` | No | 30/min | No | CSRF state token (JWT-signed, 5min expiry) |
| POST | `/auth/github/callback` | No | 10/min | No | GitHub OAuth callback — creates/updates user, returns JWT |
| GET | `/auth/me` | JWT | 30/min | 30s Redis | Current user profile |
| POST | `/auth/refresh` | JWT | No limit | No | Refresh JWT, update last_login |

**Auth flow:**
1. Frontend initiates GitHub OAuth via NextAuth
2. After GitHub redirect, frontend calls `POST /auth/github/callback` with user profile data + signed state token
3. Backend creates or updates user, returns JWT (7-day expiry) as both JSON body and `ic_token` HttpOnly cookie
4. Protected routes decode JWT from `Authorization: Bearer` header or cookie

**Dependencies:**
- `get_current_user` — extracts JWT, loads user from DB, raises 401 on failure
- `get_optional_current_user` — same but returns `None` instead of error

### GitHub Routes (`app/routes/github.py`)

| Method | Path | Auth | Rate Limit | Cache | Description |
|--------|------|------|------------|-------|-------------|
| POST | `/github/analyze/{username}` | JWT | 5/min | No | Full skill analysis: fetch repos → build fingerprint → generate vector → store |
| GET | `/github/user/{username}` | No | 30/min | 1hr stale-while-revalidate | Proxy GitHub user profile |
| GET | `/github/fingerprint` | JWT | 30/min | No | Return stored skill JSON |

**Analysis pipeline:** `fetch repos → AI skill analysis (Groq) or regex fallback → vector embedding (Jina) or hash fallback → store to DB → invalidate user cache`

### Issues Routes (`app/routes/issues.py`)

| Method | Path | Auth | Rate Limit | Cache | Description |
|--------|------|------|------------|-------|-------------|
| GET | `/issues/matches` | JWT | 30/min | 5min | Personalized vector similarity matches with scoring |
| POST | `/issues/index` | JWT | 3/min | No | Trigger background indexing of all languages |
| POST | `/issues/save/{id}` | JWT | 30/min | No | Bookmark an issue |
| GET | `/issues/saved` | JWT | 30/min | No | List saved issues with repo info |
| GET | `/issues/search` | No | 30/min | 30min | Keyword search with GitHub API fallback |
| GET | `/issues/trending` | No | 30/min | 1hr | Trending issues from popular repos |
| GET | `/issues/smart-search` | Optional | 20/min | 10min | NL semantic search with AI query parsing |
| GET | `/issues/stats` | No | 30/min | 5min | Platform statistics |

### Search Routes (`app/routes/searches.py`)

| Method | Path | Auth | Rate Limit | Cache | Description |
|--------|------|------|------------|-------|-------------|
| GET | `/searches/suggestions` | No | 30/min | No | Language autocomplete with issue counts |
| POST | `/searches/save` | JWT | 30/min | No | Persist a search query |
| GET | `/searches/` | JWT | 30/min | No | List user's saved searches |
| GET | `/searches/{id}` | JWT | 30/min | No | Single saved search detail |
| PUT | `/searches/{id}` | JWT | 30/min | No | Update name/notify flag |
| DELETE | `/searches/{id}` | JWT | 30/min | No | Delete saved search |
| POST | `/searches/{id}/check` | JWT | 20/min | No | Re-run search, report new results |

### Maintainer Routes (`app/routes/maintainer.py`)

| Method | Path | Auth | Rate Limit | Cache | Description |
|--------|------|------|------------|-------|-------------|
| GET | `/maintainer/overview` | JWT | 20/min | 5min | Aggregated stats: repos, open issues, GFI, HW, complexity |
| GET | `/maintainer/repos/{repo_id}` | JWT | 30/min | No | Repo detail with all open issues |
| GET | `/maintainer/repos/{repo_id}/contributors` | JWT | 10/min | No | Match users by skill overlap with repo issues |

### System Routes (`main.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | API metadata (name, version, docs URL) |
| HEAD | `/health` | No | Quick liveness check (HEAD alternative) |
| GET | `/health` | No | Full health: DB ping, Redis ping, pool stats, AI status, cache metrics |
| GET | `/metrics` | API key | Request metrics: count, avg/p99 latency, cache hit rate |

---

## 5. Service Layer (Core Logic)

### Search Service (`app/services/search_service.py`)

The heart of the query → results pipeline.

**`parse_natural_query(query) → SearchIntent`**
- Primary path: Groq LLM parses the query into structured `SearchIntent` (languages, difficulty, labels, keywords, categories)
- Fallback path: 7 regex-based analyzers for languages (42 aliases), difficulty terms (3 tiers), labels (2 types), categories (7 domains), and keyword extraction

**`SearchIntent` dataclass:**
```python
@dataclass
class SearchIntent:
    keywords: List[str]
    languages: List[str]
    difficulty: Optional[str]    # beginner | intermediate | advanced
    labels: List[str]           # good_first | help_wanted
    topics: List[str]
    categories: List[str]       # frontend, backend, database, devops, ai_ml, mobile, systems
    raw_query: str
```

**`smart_search(db, query, user, ...) → (results, intent)`**
1. Parse natural query → `SearchIntent`
2. `_db_search()` — SQLAlchemy query against indexed issues:
   - ILIKE filters on language (repository), keyword (title/body), difficulty (complexity_score thresholds), labels (boolean flags)
   - Join Issue↔Repository, sorted by `updated_at DESC`
   - Uses `offset`-tolerant `pool_size` to ensure enough results for pagination
3. `_github_fallback()` — if DB results are sparse, supplement with live GitHub API results
4. `_apply_semantic_scoring()` — if user has a skill vector, compute `cosine_similarity` against issue vectors and blend with keyword score (60% keyword + 40% semantic)
5. `re_rank_results()` — full scoring engine for authenticated users: skill similarity, repo activity, freshness, interest match, popularity (60% personal + 40% original)
6. Sort by score, slice for pagination

**`expand_query(intent) → str`** — Converts intent back to search terms for GitHub API fallback

**`get_suggestions(db, prefix) → list`** — Auto-complete for search bar: queries distinct `primary_language` values with ILIKE prefix match, returns counts of open issues per language

### Matching Service (`app/services/matching_service.py`)

**`get_matched_issues(db, user, limit, offset, filters) → list`**
- Core personalized matching endpoint
- Fetches open issues with non-null `skill_vector`
- Uses a pool of `min(max(offset + limit, limit * 5), 500)` to handle deep pagination correctly
- For each (issue, repo) pair:
  1. Compute `cosine_similarity(user_vector, issue_vector)` — primary skill match
  2. Compute 4 scoring dimensions: repo activity, freshness, interest match, popularity
  3. `compute_final_score()` — weighted combination (50% skill, 15% popularity, 15% interest, 10% activity, 10% freshness)
  4. Generate AI-powered match explanation (if available) or rule-based explanation
  5. Find specific overlapping skills for `matching_skills` list

**`search_issues_keyword(db, query, filters) → list`** — Direct SQL-level keyword search with ILIKE on title/body, difficulty/complexity mapping, label booleans

**`cosine_similarity(vec_a, vec_b) → float`** — NumPy vector dot product / (norm_a × norm_b)

**`find_matching_skills(user_skills, issue_skills) → list`** — Set intersection of user languages/topics/top_skills with issue category skills

### Scoring Service (`app/services/scoring_service.py`)

Weight formula:
```python
SCORE_WEIGHTS = {
    "skill_match": 0.50,    # Vector cosine similarity
    "popularity": 0.15,     # Issue comments + repo stars/forks
    "interest_match": 0.15, # User languages/topics vs issue categories/labels
    "repo_activity": 0.10,  # Stars, recency, forks, archived flag
    "freshness": 0.10,      # Issue age (newer = higher)
}
```

Each dimension is computed independently, then blended into a final 0-1 score.

**`compute_repo_activity_score(repo)`** — 0.0 if archived, +0.2 for 10k+ stars, +0.15 for recent index, +0.1 for 100+ forks

**`compute_freshness_score(issue)`** — 1.0 for <7 days, 0.8 for <30, 0.5 for <90, 0.2 for older

**`compute_popularity_score(issue, repo)`** — Comments (0.3 for 20+), stars (0.4 for 10k+), forks (0.2 for 1k+)

**`compute_interest_match(user_skills, issue_skills)`** — Set intersection of user languages/topics/categories/skills with issue categories/labels

**`explain_score(...)`** — Human-readable: "Good match (72%) — your python, fastapi skills align (popular repo, very active, recently updated)"

### GitHub Service (`app/services/github_service.py`)

Redis-backed GitHub REST API client with stale-while-revalidate caching and rate-limit tracking.

**All HTTP routed through `_gh_request(method, url)`** which:
- Tracks `X-RateLimit-Remaining` globally
- Logs warnings at <100 remaining
- Sleeps 1s at <10 remaining
- Uses shared `httpx.AsyncClient` with connection pooling

**Endpoints cached in Redis:**

| Function | Cache Key | TTL | Data |
|----------|-----------|-----|------|
| `fetch_user()` | `gh:user:{username}` | 1hr | Public profile |
| `fetch_user_repos()` | `gh:repos:{username}` | 30min | All repos (paginated) |
| `fetch_repo_languages()` | `gh:lang:{full_name}` | 24hr | Language byte counts |
| `fetch_issues_for_repo()` | `gh:issues:{name}:{labels}:{state}` | 10min | Filtered issues |
| `search_issues_global()` | `gh:search-global:{md5}` | 10min | Label-based search |
| `search_issues_free_text()` | `gh:search-text:{md5}` | 10min | Full-text search |
| `search_trending_repos()` | `gh:trending:{lang}:{page}` | 30min | Popular repos |

All use `cache_get_with_stale()` for probabilistic early expiry.

### Skill Service (`app/services/skill_service.py`)

**`build_skill_fingerprint(repos, languages_map) → dict`**
1. Try AI (Groq) via `analyze_skills_with_ai(repos)` — sends repo summaries to LLM, gets JSON with languages, top_skills, categories, experience_level
2. Fallback: `_build_fingerprint_regex()` — counts languages/topics from repo data, maps to 7 categories, determines experience from repo count

**Merging strategy (`_merge_ai_fingerprint`):**
- Normalize AI-detected languages against actual byte counts from `languages_map`
- Fill missing top_skills from language/topic counts
- Fill missing categories from regex-based category mapping
- Downgrade experience if repo count < 5

**Vector generation (`skill_fingerprint_to_vector`):**
1. If Jina AI available: build summary text (top 5 languages, top 10 skills, experience, categories), generate 128-dim embedding
2. Fallback `_skill_fingerprint_to_vector_hash()`: deterministic hash-based vector — first 64 dims for languages, next 32 for topics, last 32 for categories, L2-normalized

**Issue vector generation (`issue_text_to_vector`):**
1. If Jina AI available: embed `title\nbody\nLabels: ...`
2. Fallback `_issue_text_to_vector_hash()`: similar hash approach, detecting language names in text, topic keywords, and category matches

**Complexity computation (`_compute_complexity`):**
- Simple indicators (beginner, easy, documentation, typo) → 0.2
- Complex indicators (architecture, security, performance) → 0.8
- Word count heuristic: <30 words → 0.35, >300 → 0.65
- Default: 0.5

### AI Service (`app/services/ai_service.py`)

**4 Groq LLM prompts + 1 vector prompt:**

| Prompt | Temperature | Max Tokens | Input | Output |
|--------|-------------|------------|-------|--------|
| `skill_analysis` | 0.2 | 1024 | Repo summaries (name, lang, desc, topics, stars) | Languages, top_skills, categories, experience_level |
| `issue_analysis` | 0.2 | 1024 | Title, body, labels | Skills, categories, complexity (0-1), effort, type |
| `match_explanation` | 0.3 | 256 | User skills + issue requirements + score | Explanation, confidence, key_match |
| `query_parsing` | 0.1 | 1024 | Natural language search query | Languages, difficulty, labels, keywords, categories, expanded_query |
| `vector_text` | 0.2 | 256 | Skill fingerprint | Dense description paragraph |

**Caching strategy:**
- AI responses cached in Redis with deterministic MD5-based keys
- Cache TTLs: 1hr (general), 24hr (queries, skills, embeddings)
- In-flight request deduplication via `asyncio.Task` registry per cache key

**Concurrency control:** `asyncio.Semaphore(5)` limits concurrent AI API calls to prevent rate-limit overwhelm

**Retry policy:** `tenacity` with `stop_after_attempt(3)` and `wait_exponential(multiplier=1, min=1, max=10)` for Groq calls

### Matching Service (`app/services/matching_service.py`)

**Notification matching (`match_event_to_listeners`) — *partial implementation*:**
- Receives webhook-like event notifications
- Matches events against listener criteria
- Uses `random.choice()` for subscriber assignment (guarded against empty list)

---

## 6. AI/ML Pipeline

### Full Analysis Pipeline (triggered by `POST /github/analyze/{username}`)

```
1. fetch_user_repos(username)
   │
   ▼
2. For each repo: fetch_repo_languages(full_name)   [parallel]
   │
   ▼
3. build_skill_fingerprint(repos, languages_map)
   │
   ├─ AI path (Groq): analyze_skills_with_ai(repos)
   │   └─ Sends top 20 repos (non-fork) to LLM as JSON
   │   └─ Receives structured skill fingerprint
   │   └─ Merges with actual byte-count data
   │
   └─ Fallback: _build_fingerprint_regex(repos, languages_map)
       └─ Counts languages, topics; maps to 7 categories
       └─ Determines experience: <5 = beginner, <20 = intermediate, 20+ = advanced
   │
   ▼
4. skill_fingerprint_to_vector(fingerprint)
   │
   ├─ AI path (Jina): Generate summary text → POST /v1/embeddings → 128-dim vector
   │
   └─ Fallback: _skill_fingerprint_to_vector_hash(fingerprint)
       └─ Deterministic hash-based: 64 dims languages, 32 dims topics, 32 dims categories
       └─ L2-normalized
   │
   ▼
5. Store to User model: skill_json, skill_vector, skill_last_updated
```

### Issue Indexing Pipeline (triggered by `POST /issues/index` or ARQ cron)

```
For each (language, label) pair:
   │
   ▼
1. search_issues_global(language, label)
   │  └─ GitHub API: /search/issues?q=label:"{label}"+language:{language}
   │
   ▼
2. Upsert repositories (ON CONFLICT DO NOTHING on full_name)
   │
   ▼
3. For each new issue (parallel via asyncio.gather):
   ├─ extract_required_skills(title, body, labels)
   │   └─ AI (Groq) or regex fallback
   └─ issue_text_to_vector(title, body, labels)
       └─ AI (Jina) or hash fallback
   │
   ▼
4. Upsert issues (ON CONFLICT DO NOTHING on github_id)
   │
   ▼
5. Commit transaction
```

### NL Query Parsing Pipeline (triggered by `GET /issues/smart-search`)

```
Natural language query
   │
   ▼
parse_natural_query(query)
   │
   ├─ AI path (Groq, deterministic): parse_query_with_ai(query)
   │   └─ Returns: {languages, difficulty, labels, keywords, categories, expanded_query}
   │
   └─ Fallback (7 regex analyzers):
       ├─ Difficulty detection (3 tiers × 60 terms)
       ├─ Language detection (42 aliases mapped to 20+ canonical names)
       ├─ Label detection (good_first, help_wanted)
       ├─ Category detection (7 domains × 60+ keywords)
       └─ Keyword extraction (remove matched phrases, filter >2 chars)
   │
   ▼
SearchIntent → _db_search() + _github_fallback()
   │
   ▼
_scoring + re-ranking → sorted results
```

### Semantic Matching (triggered by `GET /issues/matches`)

```
User.skill_vector (128-dim)  ←→  Issue.skill_vector (128-dim)
            │
            ▼
    cosine_similarity(a, b)
            │
            ▼
    Weighted blend with:
    ├─ repo_activity  (10%)
    ├─ freshness      (10%)
    ├─ interest_match (15%)
    ├─ popularity     (15%)
    └─ skill_similarity (50%)
            │
            ▼
    Final_score (0-1) → sorted feed
```

---

## 7. Database Layer

### Connection Architecture

**`app/core/database.py`:**

```python
engine = create_async_engine(
    DATABASE_URL,                    # postgresql+asyncpg://...
    pool_pre_ping=True,              # Validate connection before use
    pool_use_lifo=True,              # Reuse hottest connection
    pool_size=3,                     # Per-process pool: 3 conns
    max_overflow=2,                  # Burst: +2 = max 5/process
    pool_recycle=300,               # 5 min recycle (PgBouncer compat)
    pool_timeout=5,                  # Fail fast if pool exhausted
    connect_args={
        "timeout": 10,
        "statement_cache_size": 0,          # asyncpg <0.28
        "prepared_statement_cache_size": 0,  # asyncpg >=0.28
        "command_timeout": 30,
    },
    isolation_level="READ_COMMITTED",
)
```

**PgBouncer compatibility:** Both `statement_cache_size=0` and `prepared_statement_cache_size=0` are set to cover all asyncpg versions and fully disable prepared statement caching, preventing `InvalidSQLStatementNameError` and `DuplicatePreparedStatementError` that occur when PgBouncer transaction pooling routes successive transactions to different backends.

**Startup isolation:** `init_db()` uses its own short-lived engine (not the application pool) to create the vector extension, preventing startup queries from polluting the shared pool's prepared-statement state.

**Shutdown:** `close_db()` disposes the engine pool on graceful shutdown, releasing all connections back to PgBouncer.

**Pool monitoring:** SQLAlchemy event listeners on `engine.sync_engine` for `connect`, `checkin`, and `checkout` events provide diagnostics logging. Pool status (size, in-use, overflow) exposed in `/health` endpoint.

**Rate limiting:** `pool_size=3` + `max_overflow=2` per worker process gives max 5 connections per Gunicorn worker. With 2 workers (default `WEB_CONCURRENCY`), max 10 connections. This stays within Supabase free tier's 15-connection limit.

### Migration Engine (`alembic/env.py`)

- Reads `DATABASE_URL_DIRECT` first (bypasses PgBouncer for DDL), falls back to `DATABASE_URL`
- Uses `NullPool` + both cache size parameters set to 0
- `DATABASE_URL_DIRECT` env var allows using a direct Postgres connection (port 5432) for schema changes while the application uses the pooled connection (port 6543)

### Reconciliation Script (`scripts/db_reconcile.py`)

Pre-flight check before `alembic upgrade head` in the Docker CMD:
- Checks if `alembic_version` table exists in `information_schema`
- If it doesn't but `users` table exists, runs `alembic stamp head` to prevent `DuplicateTableError`
- Uses a separate engine with `NullPool` and both cache size parameters

---

## 8. Caching & Redis

### Infrastructure

- **Provider:** Upstash (serverless Redis, TLS via `rediss://`)
- **Max connections:** 20
- **Timeouts:** connect=3s, socket=3s
- **Retry:** Exponential backoff, 3 retries
- **Health check interval:** 30s

### Three Distinct Roles

#### 1. API Response Cache (`app/core/cache.py`)

All expensive endpoints cache results with Redis. Graceful degradation: when Redis is down, `cache_get()` returns `None`, `cache_set()` returns `False`, and routes recompute from DB/GitHub.

**Key prefix:** `ic:` (configurable via `REDIS_PREFIX`)

**Cache features:**
- Probabilistic early expiry (stampede protection) — randomizes cache refresh before TTL hits zero
- In-flight request deduplication — concurrent requests for the same key wait on one task
- Hit/miss counters with rolling latency window (avg, p99)
- `cache_get_with_stale()` — stale-while-revalidate pattern: serve stale, refresh in background
- `cache_delete_pattern()` — SCAN + DEL for glob pattern invalidation (used after indexing)

**Key TTLs by endpoint:** 5min (matches), 10min (smart search), 30min (keyword search), 1hr (trending, stats)

#### 2. Rate Limiting (`app/core/ratelimit.py`)

Uses slowapi with Redis for distributed rate counters:
- Default: 60 requests/minute
- Auth endpoints: 5-10/minute
- Expensive/AI endpoints: 20-30/minute
- Indexing: 3/minute
- Keyed by JWT `sub` for authenticated users, client IP for anonymous
- Falls back to in-memory for remote Redis to avoid connection error crashes

#### 3. Background Job Queue (`app/worker.py`)

ARQ runs three job types:
- `full_index` — Index all languages with GFI+HW labels, then invalidate trending cache
- `index_language_issues` — Single language/label indexing with semaphore(3) concurrency
- `check_saved_searches` — Re-evaluate saved searches, log new results (run by ARQ cron)

Worker `shutdown` disposes the DB engine pool.

### Cache Invalidation Strategy

| Event | Invalidation |
|-------|-------------|
| Profile analysis | `auth:me:{user.id}` deleted |
| Full index complete | `trending:*` pattern deleted |
| Token refresh | `auth:me:{user.id}` deleted |
| Data update | Route-level TTL expiration + probabilistic early expiry |

---

## 9. Infrastructure & Deployment

### Docker Containers (4 services)

| Service | Image | Port | Memory Limit |
|---------|-------|------|-------------|
| `db` | pgvector/pgvector:pg16 | 5432 | — |
| `redis` | redis:7-alpine | 6379 | — |
| `backend` | Custom (multi-stage) | 8000 | 512M / 256M |
| `frontend` | Custom (Next.js standalone) | 3000 | 512M / 256M |

### Multi-Stage Build (`Dockerfile`)

```
Stage 1: Node 20 → npm ci → next build
Stage 2: Python 3.12 → pip install deps
Stage 3: Python 3.12 slim → Nginx + compiled deps + app code
```

**Production image size:** ~250MB with Nginx, Python, compiled C extensions

### Startup Sequence (`start.sh`)

```
1. Nginx config: substitute ${PORT} from env
2. cd /app/backend
3. gunicorn main:app (2 workers, uvcoorn, port 8000) &
4. cd /app/frontend
5. node server.js (port 3000) &
6. nginx -g 'daemon off;' (reverse proxy, port ${PORT:-8080})
```

**Alternative (production Docker CMD in backend/Dockerfile):**
```
python -m scripts.db_reconcile 2>&1
  && alembic upgrade head 2>&1
  && exec gunicorn main:app ...
```

### Nginx Configuration

- Routes `/api/v1/*`, `/health`, `/docs` → backend (port 8000)
- Routes everything else → frontend (port 3000)
- Auto `worker_processes`
- Logs to stdout/stderr

### Docker Compose

- `depends_on` with health checks: `db` (pg_isready), `redis` (redis-cli ping)
- Internal Docker network with outbound access for GitHub API / AI providers
- Environment variables from host or .env
- Memory limits per container

### Production Checklist

1. **Secrets:** `SECRET_KEY`, `GITHUB_TOKEN`, `GITHUB_CLIENT_*`, `GROQ_API_KEY`, `JINA_API_KEY`, `METRICS_API_KEY`
2. **Database:** Managed PostgreSQL with pgvector (Supabase, RDS, etc.)
3. **Redis:** Managed Redis via Upstash, ElastiCache, or Redis Cloud (use `rediss://` for TLS)
4. **CORS:** Set `FRONTEND_URL` and/or `ALLOW_ORIGINS`
5. **Cookie security:** `COOKIE_SECURE=true` (requires HTTPS)
6. **Database URLs:** `DATABASE_URL` (pooled, port 6543 for PgBouncer) + `DATABASE_URL_DIRECT` (direct, port 5432 for migrations)

---

## 10. Testing Strategy

### Test Suite (84 tests, 2 skipped)

```
tests/
├── conftest.py                     # Env overrides, mock Redis data
├── test_routes.py                  # 47 tests — all endpoints
├── test_github_service.py          # Mocked HTTP tests
├── test_search_service.py          # Query parsing, expansion, relevance
├── test_scoring_service.py         # All scoring dimensions
├── test_matching_service.py        # Notification matching
└── test_skill_service.py           # Fingerprinting, hashing, vectors
```

**Test infrastructure (`conftest.py`):**
- Overrides env vars: `DATABASE_URL` (local test DB), `AI_ENABLED=false`, `GROQ_API_KEY=""`, `METRICS_API_KEY=""`
- Sets a test `SECRET_KEY` to avoid the default-key warning
- Prevents real API calls and .env interference

**Coverage areas:**

| Module | Tests | What's tested |
|--------|-------|---------------|
| Routes | 47 | Auth (4), Issues (15), GitHub (6), Search (10), Maintainer (5), Metrics (3), CORS (1), Smart search (2), Index (1) |
| Scoring | 14 | Archived repos, star thresholds, freshness decay, popularity tiers, interest overlap, final weights, explanation generation |
| Search | 12 | Language detection, difficulty tiers, labels, keywords, advanced queries, edge cases, expansion, relevance |
| Skills | 9 | Deterministic hashing, fingerprint structure, category mapping, vector shape, complexity extraction |
| GitHub | 1 | Cached fetch wrapper |
| Matching | 1 | Notification matching logic |

**Test patterns:**
- HTTP tests use FastAPI `TestClient` with async
- Redis mocked via `cache_ping: true` fixture
- Time-sensitive tests use frozen `datetime.now()`
- GitHub service tests mock `httpx` responses

**Skipped tests:** 2 GitHub integration tests excluded from CI (require live API access)

---

## 11. Security Architecture

### Authentication

- **GitHub OAuth** via NextAuth (frontend) + custom `/auth/github/callback` (backend)
- **JWT tokens** (HS256, 7-day expiry) with `sub` = user ID
- Token delivered as both `Authorization: Bearer` header and `ic_token` HttpOnly cookie
- State parameter (signed JWT, 5-min expiry) prevents CSRF on OAuth callback

### Authorization

- Route-level guards via `Depends(get_current_user)` and `Depends(get_optional_current_user)`
- Maintainer routes verify `repo.owner_login == user.github_username` before returning data

### Rate Limiting

| Tier | Limit | Applied To |
|------|-------|------------|
| Default | 60/min | General endpoints |
| Strict | 20-30/min | Search, matches, profile |
| Auth | 5-10/min | OAuth callback, state |
| Expensive | 3-5/min | Indexing, AI analysis |
| Metrics | 30/min | Health, metrics |

Keyed by JWT `sub` (authenticated) or client IP (anonymous). Uses `X-Real-IP` / `X-Forwarded-For` for proxy-aware IP detection.

### Data Protection

- Passwords: None (OAuth-only authentication)
- API keys: `METRICS_API_KEY` protects `/metrics` endpoint
- Secrets: All in environment variables, not in code
- CORS: Whitelist-based, supports multiple origins

### Error Handling

- Generic exception handler returns `error_id` (request UUID) in 500 responses
- Structured logging with request ID traceability
- Catch-all exception handler prevents information leakage

---

## 12. Observability

### Logging

| Logger | Format | Content |
|--------|--------|---------|
| `issuecompass` | `[level] name: message` | App-level events (startup, config, DB, Redis) |
| `issuecompass.http` | `[req_id] METHOD path STATUS duration` | Every request (via middleware) |
| `issuecompass.worker` | `[level] name: message` | ARQ worker events |
| DB pool events | `[DEBUG]` | Connection create, checkin, checkout |

**Request ID:** Generated from `X-Request-ID` header or UUID, attached to `request.state.request_id`, included in all log lines and error responses.

### Metrics

**HTTP metrics** (`/metrics`):
- Total requests
- Average duration (seconds)
- P99 duration (seconds)
- Recent request count (rolling window of 1000)

**Cache metrics** (included in `/health` and `/metrics`):
- Available (bool)
- Hits, misses, total, hit rate %
- Average latency (ms)
- P99 latency (ms)
- In-flight dedup count

**Pool metrics** (included in `/health`):
- Size, checked_in, checked_out, overflow

### Health Check (`GET /health`)

Returns:
- `status`: "ok" or "degraded"
- `database`: boolean (SELECT 1 ping)
- `redis`: boolean (PING with auto-reconnect)
- `ai_enabled`: boolean (config check)
- `pool`: connection pool stats
- `cache`: cache statistics
- `config_errors`: list of configuration issues
- `metrics`: request metrics

---

## 13. Appendix: File Map

### Backend Structure

```
backend/
├── main.py                          # FastAPI app, lifespan, routes, middleware
├── requirements.txt                 # Python dependencies (20 packages)
├── Dockerfile                       # Multi-stage production build
├── ENGINEERING_REPORT.md            # Previous hardening report
├── PGBOUNCER_ENGINEERING_REPORT.md  # PgBouncer fix report
│
├── app/
│   ├── __init__.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                # Pydantic Settings (22 env vars)
│   │   ├── database.py              # Async engine, session, init_db, close_db
│   │   ├── cache.py                 # Redis cache (get/set/delete/ping/stats)
│   │   ├── monitoring.py            # Request logging middleware, metrics
│   │   ├── ratelimit.py             # SlowAPI limiter configuration
│   │   ├── route_cache.py           # @cached_response decorator
│   │   ├── github_cache.py          # Redundant cache layer for GitHub
│   │   └── utils.py                 # parse_dt() utility
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py                # User, Repository, Issue, SavedIssue, SavedSearch
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── schemas.py               # Pydantic models for all API responses
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py                  # /auth/* — JWT + OAuth
│   │   ├── github.py                # /github/* — Profile analysis
│   │   ├── issues.py                # /issues/* — Matches, search, trending
│   │   ├── searches.py              # /searches/* — Saved searches
│   │   └── maintainer.py            # /maintainer/* — Dashboard
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_service.py            # Groq LLM + Jina embeddings (445 lines)
│   │   ├── github_service.py        # GitHub REST API client (277 lines)
│   │   ├── search_service.py        # Query parsing, smart search (489 lines)
│   │   ├── skill_service.py         # Fingerprint building, hashing (402 lines)
│   │   ├── scoring_service.py       # 5-dimension scoring engine (184 lines)
│   │   ├── matching_service.py      # Vector matching, keyword search (204 lines)
│   │   └── __init__.py
│   │
│   └── worker.py                    # ARQ background worker (276 lines)
│
├── scripts/
│   └── db_reconcile.py              # Alembic reconciliation script
│
├── alembic/
│   ├── env.py                       # Async migration engine
│   ├── script.py.mako               # Migration template
│   └── versions/
│       ├── 0001_initial_schema.py   # Users, repos, issues, saved_issues
│       ├── 0002_add_performance_indexes.py  # Composite + partial indexes
│       └── 0003_add_saved_searches_table.py # Missing table + index fix
│
└── tests/
    ├── __init__.py
    ├── conftest.py                  # Test configuration
    ├── test_routes.py               # 47 endpoint tests
    ├── test_github_service.py       # Cached fetch tests
    ├── test_search_service.py       # Query parsing tests
    ├── test_scoring_service.py      # Scoring dimension tests
    ├── test_matching_service.py     # Notification matching tests
    └── test_skill_service.py        # Fingerprint/vector tests
```

### Frontend Structure (summary)

```
frontend/
├── package.json                     # Next.js 14, Radix UI, TanStack Query, Recharts
├── Dockerfile                       # Node 20 build
├── next.config.ts                   # Standalone output, API proxy
├── tailwind.config.ts               # Custom theme config
├── tsconfig.json
├── src/
│   ├── app/                         # Next.js App Router pages
│   │   ├── layout.tsx               # Root layout, providers, navigation
│   │   ├── page.tsx                 # Landing page
│   │   ├── dashboard/               # Main dashboard (matches feed)
│   │   ├── search/                  # Search + smart search
│   │   ├── trending/                # Trending issues
│   │   ├── saved/                   # Saved issues + searches
│   │   └── maintainer/              # Maintainer dashboard
│   └── components/                  # UI components (Radix, custom)
│       ├── ui/                      # Reusable UI atoms
│       ├── layout/                  # Navbar, footer
│       └── issues/                  # Issue cards, match display
```

### Infrastructure Files

```
root/
├── Dockerfile                       # Combined multi-stage (frontend + backend + nginx)
├── docker-compose.yml               # 4 services: db, redis, backend, frontend
├── nginx.conf                       # Reverse proxy config
├── start.sh                         # Container entrypoint
├── pyproject.toml                   # Ruff config, pytest settings
├── .env.example                     # Template for all env vars
├── .env                             # Production secrets (git-ignored)
├── README.md                        # Full documentation
├── CONTRIBUTING.md                  # Contribution guidelines
└── LICENSE                          # MIT
```

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Backend Python files | 19 |
| Backend source lines | ~5,200 |
| Test files | 6 |
| Test count | 84 passing, 2 skipped |
| API endpoints | 24 |
| Database models | 5 |
| Service modules | 6 |
| Alembic migrations | 3 |
| External APIs | 3 (GitHub, Groq, Jina) |
| Docker containers | 4 |
| Third-party deps (Python) | 20 |
| Frontend deps | 27 |
| Request tracking | UUID per request |
| Rate limit tiers | 5 |
| Scoring dimensions | 5 |
| Vector dimensions | 128 |
| Cache layers | 3 (Redis + route + AI) |
