# IssueCompass — Live GitHub Issue Matching Refactor

> **Agent Instructions:** This document is a complete, self-contained implementation
> spec. Read it fully before writing a single line of code. Follow every section in
> order. Do not skip steps, do not improvise architecture. All file paths are relative
> to the project root unless stated otherwise.

---

## Table of Contents

1. [Objective & Scope](#1-objective--scope)
2. [Architecture Overview](#2-architecture-overview)
3. [Prerequisites & Constraints](#3-prerequisites--constraints)
4. [File-by-File Change Map](#4-file-by-file-change-map)
5. [Step 1 — scoring_service.py](#5-step-1--scoring_servicepy)
6. [Step 2 — github_service.py](#6-step-2--github_servicepy)
7. [Step 3 — matching_service.py](#7-step-3--matching_servicepy)
8. [Step 4 — worker.py](#8-step-4--workerpy)
9. [Step 5 — routes/issues.py](#9-step-5--routesissuespy)
10. [Step 6 — schemas/schemas.py](#10-step-6--schemasschemaspy)
11. [Step 7 — No Schema Migration Needed](#11-step-7--no-schema-migration-needed)
12. [Step 8 — Redis Key Contracts](#12-step-8--redis-key-contracts)
13. [Step 9 — Environment Variables](#13-step-9--environment-variables)
14. [Step 10 — Testing Checklist](#14-step-10--testing-checklist)
15. [Rollback Plan](#15-rollback-plan)

---

## 1. Objective & Scope

### What is broken today

`GET /api/v1/issues/matches` only queries issues that were previously indexed into the
local PostgreSQL database by the ARQ background worker. The worker runs on a fixed
schedule and crawls a static set of `(language, label)` pairs regardless of which
languages your actual users care about. This means:

- New issues on GitHub are invisible until the next cron cycle (up to 15 minutes stale).
- Users with niche languages (Rust, Zig, Elixir, etc.) get zero or near-zero results
  because those languages are not in the hardcoded crawl list.
- The DB fills up with issues that no user will ever match.

### What this refactor does

1. **Layer 1 — On-demand live fetch.** When a user requests matches, the backend fires
   parallel GitHub Search API queries built directly from that user's skill fingerprint,
   merges the live results with existing DB results, scores everything through the
   existing 5-dimension engine, and returns a unified ranked list. Live results are
   cached in Redis for 3 minutes keyed by a hash of the user's `skill_json`.

2. **Layer 2 — Smarter background worker.** The ARQ cron now reads the actual language
   distribution across all user fingerprints before deciding what to index, so it
   prioritises the languages your users actually have. It also runs a daily stale-issue
   cleanup (closed or older than 30 days).

3. **Layer 3 — Selective DB persistence.** A live-fetched issue is only upserted into
   PostgreSQL if its blended score meets a configurable threshold (default `0.65`). Below
   that threshold the issue is served from Redis only and never written to disk. This
   keeps the DB lean and relevant.

### What this refactor does NOT do

- No new database tables, no new Alembic migrations.
- No GitHub Webhooks, no GitHub App installation, no additional OAuth scopes.
- No new Python packages beyond what is already in `requirements.txt`. All code uses
  `httpx`, `asyncio`, `redis`, `sqlalchemy`, and standard library only.
- No changes to the frontend. The API response shape for `/issues/matches` is extended
  (two new optional fields) but remains backward-compatible.

---

## 2. Architecture Overview

```
GET /api/v1/issues/matches
        │
        ▼
[Check Redis: live_matches:{fingerprint_hash}]
        │
    HIT ──────────────────────────► Return cached result immediately
        │
      MISS
        │
        ├──── [Existing] DB vector similarity query (pgvector cosine)
        │         └─ issues WHERE state='open' AND skill_vector IS NOT NULL
        │
        └──── [NEW] Live GitHub Search API  (parallel, bounded)
                  ├─ query per top-3 languages from skill_json
                  └─ query per top-2 topics from skill_json
                       │
                       ▼
              [NEW] score_live_issue()   ← proxy scorer (no embedding needed)
                       │
                       ▼
              [EXISTING] Merge + deduplicate by github_id
                       │
                       ▼
              [EXISTING] re_rank_results() / scoring engine
                       │
                       ├── score >= PERSIST_THRESHOLD (0.65)
                       │       └─► async background upsert to PostgreSQL
                       │               + generate & store skill_vector
                       │
                       └── score < PERSIST_THRESHOLD
                               └─► ephemeral only (Redis, no DB write)
                       │
                       ▼
              [NEW] Cache unified result in Redis (TTL 3 min)
                       │
                       ▼
              Return ranked list to user
```

```
ARQ Worker (every 15 min)
        │
        ├── [NEW] Query: top-10 languages by user count from skill_json
        ├── [EXISTING] index_language(lang, labels) for each
        └── [NEW] Daily cleanup: DELETE issues WHERE state='closed'
                                   OR updated_at < NOW() - INTERVAL '30 days'
```

---

## 3. Prerequisites & Constraints

### Read before touching any file

- **Python version:** 3.11+. Use `asyncio.gather`, `asyncio.Semaphore`, and
  `asyncio.create_task` freely.
- **GitHub API rate limits:** Authenticated requests get 5,000/hr. Unauthenticated
  get 60/hr. The `github_service.py` already tracks `X-RateLimit-Remaining`. All new
  API calls MUST go through `github_service._gh_request()` — never call `httpx`
  directly from matching or scoring services.
- **Semaphore budget:** `ai_service.py` already holds a `asyncio.Semaphore(5)` for AI
  calls. For GitHub parallel queries introduce a separate `asyncio.Semaphore(4)` defined
  in `github_service.py`. Never exceed 4 concurrent GitHub requests per user call.
- **Redis key naming:** All new keys follow the existing pattern
  `{prefix}:{identifier}`. New keys defined in Section 12.
- **Do not break existing endpoints.** Every existing test in `tests/` must still pass.
  Run `pytest` after each step.
- **Scoring weights are sacred.** Do not touch `SCORE_WEIGHTS` in `scoring_service.py`.
  The new `score_live_issue()` function is a *proxy* that feeds the same downstream
  `re_rank_results()` pipeline — it does not replace any existing scorer.

---

## 4. File-by-File Change Map

| File | Type of change |
|------|----------------|
| `app/services/scoring_service.py` | ADD `score_live_issue()` function |
| `app/services/github_service.py` | ADD `fetch_live_issues_for_user()`, ADD module-level semaphore |
| `app/services/matching_service.py` | REFACTOR `get_matched_issues()` to merge live + DB, ADD `_persist_high_score_issues()` |
| `app/worker.py` | REFACTOR `index_issues_task()` to be user-demand-aware, ADD `cleanup_stale_issues()` |
| `app/routes/issues.py` | MINOR: pass `user.skill_json` into matching service call |
| `app/schemas/schemas.py` | ADD two optional fields to `IssueMatch` response schema |
| No other files need changes | — |

---

## 5. Step 1 — scoring_service.py

**File:** `backend/app/services/scoring_service.py`

**Goal:** Add `score_live_issue()` — a proxy scorer that produces a 0–1 composite score
for a raw GitHub API issue dict (which has no `skill_vector` yet). This score feeds
directly into the same `re_rank_results()` call used for DB issues.

### Add after the existing `compute_interest_match()` function

```python
# ---------------------------------------------------------------------------
# Live-issue proxy scorer
# Produces a 0–1 composite for a raw GitHub API issue dict.
# Called BEFORE the issue is embedded or persisted.
# ---------------------------------------------------------------------------

def score_live_issue(
    user_skills: dict,
    raw_issue: dict,
    raw_repo: dict,
) -> float:
    """
    Compute a blended 0-1 score for a live GitHub issue that has not yet been
    embedded or stored in the database.

    Parameters
    ----------
    user_skills : dict
        The user's skill_json field:
        {languages: {lang: pct}, topics: [], categories: {}, experience_level: str,
         top_skills: []}
    raw_issue : dict
        A single item from the GitHub Search API response (issues search endpoint).
        Expected keys: title, body, labels, created_at, updated_at, comments,
                       pull_request (presence = PR, skip it), repository (nested dict).
    raw_repo : dict
        The repository sub-object from the same API response. May overlap with
        raw_issue["repository"] but is passed explicitly for clarity.

    Returns
    -------
    float
        Composite score in [0.0, 1.0]. Higher = better match for this user.
    """
    # Skip pull requests (GitHub search returns PRs in issue search)
    if raw_issue.get("pull_request"):
        return 0.0

    user_languages = {k.lower() for k in user_skills.get("languages", {}).keys()}
    user_topics = {t.lower() for t in user_skills.get("topics", [])}
    user_top_skills = {s.lower() for s in user_skills.get("top_skills", [])}
    user_categories = set(user_skills.get("categories", {}).keys())

    # ── 1. Language match (weight 0.40) ──────────────────────────────────────
    repo_language = (raw_repo.get("language") or "").lower()
    repo_topics = {t.lower() for t in (raw_repo.get("topics") or [])}

    lang_score = 0.0
    if repo_language and repo_language in user_languages:
        # Bonus proportional to how much of the user's portfolio is this language
        lang_pct = user_skills.get("languages", {}).get(repo_language, 0)
        lang_score = min(1.0, 0.5 + lang_pct * 0.5)  # 0.5 base + up to 0.5 bonus
    elif repo_language:
        lang_score = 0.0

    # ── 2. Topic / interest match (weight 0.20) ───────────────────────────────
    topic_overlap = len(user_topics & repo_topics)
    topic_score = min(1.0, topic_overlap * 0.35)

    # ── 3. Label match (weight 0.15) ─────────────────────────────────────────
    label_names = {lbl["name"].lower() for lbl in raw_issue.get("labels", [])}
    label_score = 0.0
    if "good first issue" in label_names:
        label_score += 0.6
    if "help wanted" in label_names:
        label_score += 0.3
    if "bug" in label_names:
        label_score += 0.1
    label_score = min(1.0, label_score)

    # ── 4. Freshness (weight 0.15) ────────────────────────────────────────────
    # Re-use existing freshness scorer via a lightweight shim
    from datetime import datetime, timezone

    updated_str = raw_issue.get("updated_at") or raw_issue.get("created_at", "")
    freshness_score = 0.2  # default: old
    if updated_str:
        try:
            updated_dt = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - updated_dt).days
            if age_days <= 7:
                freshness_score = 1.0
            elif age_days <= 30:
                freshness_score = 0.8
            elif age_days <= 90:
                freshness_score = 0.5
            else:
                freshness_score = 0.2
        except (ValueError, TypeError):
            freshness_score = 0.2

    # ── 5. Repo popularity (weight 0.10) ──────────────────────────────────────
    stars = raw_repo.get("stargazers_count") or raw_repo.get("stars", 0)
    forks = raw_repo.get("forks_count") or raw_repo.get("forks", 0)
    pop_score = 0.0
    if stars >= 10_000:
        pop_score += 0.4
    elif stars >= 1_000:
        pop_score += 0.25
    elif stars >= 100:
        pop_score += 0.1
    if forks >= 1_000:
        pop_score += 0.2
    elif forks >= 100:
        pop_score += 0.1
    comments = raw_issue.get("comments", 0)
    if comments >= 20:
        pop_score += 0.3
    elif comments >= 5:
        pop_score += 0.15
    pop_score = min(1.0, pop_score)

    # ── Composite (weights must sum to 1.0) ───────────────────────────────────
    composite = (
        lang_score    * 0.40 +
        topic_score   * 0.20 +
        label_score   * 0.15 +
        freshness_score * 0.15 +
        pop_score     * 0.10
    )
    return round(composite, 4)
```

### Also add the following helper near the bottom of the file

```python
def build_live_issue_explanation(
    user_skills: dict,
    raw_issue: dict,
    raw_repo: dict,
    score: float,
) -> str:
    """
    Rule-based explanation string for a live issue (no AI call).
    Format mirrors the existing explain_score() output.
    """
    lang = (raw_repo.get("language") or "unknown").lower()
    pct = int(score * 100)
    label_names = [lbl["name"] for lbl in raw_issue.get("labels", [])]
    label_str = ", ".join(label_names[:3]) if label_names else "no labels"
    stars = raw_repo.get("stargazers_count") or raw_repo.get("stars", 0)
    repo_name = raw_repo.get("full_name") or raw_repo.get("name", "")

    quality = "Excellent" if score >= 0.8 else "Good" if score >= 0.6 else "Partial"
    return (
        f"{quality} match ({pct}%) — {lang} repo '{repo_name}' "
        f"[{label_str}], {stars:,} stars (live result)"
    )
```

---

## 6. Step 2 — github_service.py

**File:** `backend/app/services/github_service.py`

**Goal:** Add `fetch_live_issues_for_user()` that builds and executes parallel GitHub
Search API queries from a user's skill fingerprint. All calls go through the existing
`_gh_request()` method to preserve rate-limit tracking and Redis caching.

### Add a module-level semaphore at the top of the file (after imports)

Find the line where the module-level `httpx.AsyncClient` or similar global is defined
and add directly below it:

```python
# Limit concurrent live-fetch queries per request to avoid rate-limit burst
_LIVE_FETCH_SEMAPHORE = asyncio.Semaphore(4)
```

### Add `fetch_live_issues_for_user()` as a new method on `GitHubService`

Place this method after `search_issues_free_text()`:

```python
async def fetch_live_issues_for_user(
    self,
    skill_json: dict,
    per_language_limit: int = 15,
    max_queries: int = 8,
) -> list[dict]:
    """
    Fetch live open issues from GitHub Search that match this user's skill
    fingerprint. Fires parallel queries (bounded by _LIVE_FETCH_SEMAPHORE)
    and returns a deduplicated flat list of raw GitHub issue dicts.

    Each returned dict is the raw GitHub Search API issue object with an
    extra key ``_repo`` containing the repository sub-object for scoring.

    Parameters
    ----------
    skill_json : dict
        User's stored skill fingerprint (languages, topics, top_skills, etc.)
    per_language_limit : int
        Max results per individual API query (GitHub max is 100; keep low).
    max_queries : int
        Cap on total parallel queries to prevent rate-limit exhaustion.

    Returns
    -------
    list[dict]
        Deduplicated raw GitHub issue dicts, each augmented with ``_repo``.
    """
    if not skill_json:
        return []

    # Build query strings from fingerprint
    queries: list[str] = []

    top_langs = sorted(
        skill_json.get("languages", {}).items(),
        key=lambda kv: kv[1],
        reverse=True,
    )[:3]

    for lang, _ in top_langs:
        queries.append(
            f'label:"good first issue" language:{lang} state:open is:issue'
        )
        queries.append(
            f'label:"help wanted" language:{lang} state:open is:issue'
        )

    top_topics = skill_json.get("topics", [])[:2]
    for topic in top_topics:
        queries.append(
            f'topic:{topic} label:"good first issue" state:open is:issue'
        )

    # Cap at max_queries
    queries = queries[:max_queries]

    async def _run_query(q: str) -> list[dict]:
        async with _LIVE_FETCH_SEMAPHORE:
            try:
                results = await self.search_issues_free_text(
                    q,
                    per_page=per_language_limit,
                )
                # Normalise: attach _repo from the nested repository field
                enriched = []
                for issue in results:
                    repo = issue.get("repository") or {}
                    issue["_repo"] = repo
                    enriched.append(issue)
                return enriched
            except Exception:
                # Individual query failure must not break the whole request
                return []

    all_results = await asyncio.gather(*[_run_query(q) for q in queries])

    # Flatten and deduplicate by GitHub issue ID
    seen_ids: set[int] = set()
    deduped: list[dict] = []
    for batch in all_results:
        for issue in batch:
            issue_id = issue.get("id")
            if issue_id and issue_id not in seen_ids:
                seen_ids.add(issue_id)
                deduped.append(issue)

    return deduped
```

### Important: verify `search_issues_free_text` signature

`search_issues_free_text` must accept a `per_page` keyword argument (integer, default
30). If the existing implementation does not have this parameter, add it:

```python
# Inside search_issues_free_text, the URL build should include:
params = {
    "q": query,
    "sort": "updated",
    "order": "desc",
    "per_page": per_page,  # ADD this line if missing
}
```

---

## 7. Step 3 — matching_service.py

**File:** `backend/app/services/matching_service.py`

**Goal:** This is the largest change. Refactor `get_matched_issues()` to:
1. Call `github_service.fetch_live_issues_for_user()` in parallel with the existing DB
   query.
2. Score live issues with the new `score_live_issue()` proxy scorer.
3. Merge and deduplicate the two result sets.
4. Cache the unified result in Redis.
5. Fire-and-forget a background task to persist high-scoring live issues to DB.

### Add the following imports at the top of `matching_service.py`

```python
import asyncio
import hashlib
import json
import logging

from app.services.scoring_service import score_live_issue, build_live_issue_explanation
# github_service import already exists — confirm it is imported as an instance or
# imported class. The call below uses the module-level singleton pattern that
# github_service.py already exposes.
```

### Add module-level constants

```python
# Redis TTL for live-match cache (seconds)
LIVE_MATCH_CACHE_TTL = 180  # 3 minutes

# Minimum composite score for a live issue to be persisted to PostgreSQL
PERSIST_SCORE_THRESHOLD = 0.65

logger = logging.getLogger("issuecompass.matching")
```

### Add helper: `_fingerprint_cache_key()`

```python
def _fingerprint_cache_key(skill_json: dict) -> str:
    """
    Deterministic Redis key for a user's live match results.
    Keyed on a hash of skill_json so two users with identical fingerprints
    share the same cached results (saves GitHub API quota).
    """
    canonical = json.dumps(skill_json, sort_keys=True, separators=(",", ":"))
    digest = hashlib.md5(canonical.encode()).hexdigest()[:16]
    return f"live_matches:{digest}"
```

### Add helper: `_convert_raw_issue_to_match_dict()`

This converts a raw GitHub API issue dict into the same shape as the existing DB-backed
match dicts so downstream re-ranking code handles them identically.

```python
def _convert_raw_issue_to_match_dict(
    raw_issue: dict,
    raw_repo: dict,
    user_skills: dict,
    proxy_score: float,
) -> dict:
    """
    Convert a raw GitHub Search API issue object into the internal match dict
    shape used by re_rank_results() and the API response serialiser.

    The resulting dict is intentionally schema-compatible with the dict
    produced for DB issues so both can pass through the same scorer.
    """
    labels = [lbl["name"] for lbl in raw_issue.get("labels", [])]
    return {
        # Core issue fields
        "id": None,                        # No DB id yet
        "github_id": raw_issue.get("id"),
        "number": raw_issue.get("number"),
        "title": raw_issue.get("title", ""),
        "body": (raw_issue.get("body") or "")[:2000],  # truncate for safety
        "html_url": raw_issue.get("html_url", ""),
        "state": "open",
        "labels": labels,
        "is_good_first_issue": "good first issue" in [l.lower() for l in labels],
        "is_help_wanted": "help wanted" in [l.lower() for l in labels],
        "comments": raw_issue.get("comments", 0),
        "created_at": raw_issue.get("created_at"),
        "updated_at": raw_issue.get("updated_at"),
        # Repository fields (flattened for scorer)
        "repo_id": None,
        "repo_full_name": raw_repo.get("full_name", ""),
        "repo_name": raw_repo.get("name", ""),
        "repo_html_url": raw_repo.get("html_url", ""),
        "repo_language": raw_repo.get("language", ""),
        "repo_stars": raw_repo.get("stargazers_count") or raw_repo.get("stars", 0),
        "repo_forks": raw_repo.get("forks_count") or raw_repo.get("forks", 0),
        "repo_topics": raw_repo.get("topics", []),
        "repo_is_archived": raw_repo.get("archived", False),
        # Scoring metadata
        "match_score": proxy_score,
        "skill_vector": None,              # Not yet embedded
        "required_skills": {},
        "complexity_score": 0.5,           # Unknown until embedded
        "matching_skills": _find_live_matching_skills(user_skills, raw_issue, raw_repo),
        "match_explanation": build_live_issue_explanation(
            user_skills, raw_issue, raw_repo, proxy_score
        ),
        # Marker so callers know this is a live (non-DB) result
        "_is_live": True,
        "_raw_github_id": raw_issue.get("id"),
    }
```

### Add helper: `_find_live_matching_skills()`

```python
def _find_live_matching_skills(
    user_skills: dict,
    raw_issue: dict,
    raw_repo: dict,
) -> list[str]:
    """Return skills that overlap between user fingerprint and live issue."""
    user_set = set()
    user_set.update(k.lower() for k in user_skills.get("languages", {}).keys())
    user_set.update(t.lower() for t in user_skills.get("topics", []))
    user_set.update(s.lower() for s in user_skills.get("top_skills", []))

    issue_set = set()
    repo_lang = (raw_repo.get("language") or "").lower()
    if repo_lang:
        issue_set.add(repo_lang)
    issue_set.update(t.lower() for t in (raw_repo.get("topics") or []))
    issue_set.update(
        lbl["name"].lower() for lbl in raw_issue.get("labels", [])
    )
    return sorted(user_set & issue_set)
```

### Add the background persistence task: `_persist_high_score_issues()`

```python
async def _persist_high_score_issues(
    live_matches: list[dict],
    db,  # AsyncSession
) -> None:
    """
    Background fire-and-forget task.
    For each live match above PERSIST_SCORE_THRESHOLD, upsert the issue into
    the PostgreSQL issues table and generate a skill_vector embedding.

    This function is called with asyncio.create_task() — exceptions are caught
    and logged, never raised to the caller.
    """
    from app.models.models import Issue, Repository
    from app.services.skill_service import issue_text_to_vector
    from sqlalchemy import select

    high_score = [
        m for m in live_matches
        if m.get("match_score", 0) >= PERSIST_SCORE_THRESHOLD
        and m.get("_raw_github_id")
    ]

    if not high_score:
        return

    for match in high_score:
        try:
            github_id = match["_raw_github_id"]

            # Check if already exists
            result = await db.execute(
                select(Issue).where(Issue.github_id == github_id)
            )
            existing = result.scalar_one_or_none()
            if existing:
                # Update freshness metadata only
                existing.updated_at = match.get("updated_at")
                existing.comments = match.get("comments", existing.comments)
                continue

            # Resolve or create repository record
            repo_result = await db.execute(
                select(Repository).where(
                    Repository.full_name == match["repo_full_name"]
                )
            )
            repo_obj = repo_result.scalar_one_or_none()
            if not repo_obj:
                repo_obj = Repository(
                    full_name=match["repo_full_name"],
                    name=match["repo_name"],
                    html_url=match["repo_html_url"],
                    primary_language=match["repo_language"],
                    stars=match["repo_stars"],
                    forks=match["repo_forks"],
                    topics=match["repo_topics"],
                    is_archived=match["repo_is_archived"],
                )
                db.add(repo_obj)
                await db.flush()

            # Generate embedding for the issue text
            issue_text = match["title"] + "\n" + match.get("body", "")
            vector = await issue_text_to_vector(issue_text)

            new_issue = Issue(
                github_id=github_id,
                number=match["number"],
                title=match["title"],
                body=match.get("body", "")[:10000],
                html_url=match["html_url"],
                state="open",
                labels=match["labels"],
                is_good_first_issue=match["is_good_first_issue"],
                is_help_wanted=match["is_help_wanted"],
                comments=match["comments"],
                skill_vector=vector,
                complexity_score=match.get("complexity_score", 0.5),
                required_skills={},
                repository_id=repo_obj.id,
            )
            db.add(new_issue)

        except Exception as exc:
            logger.warning(
                "Failed to persist live issue github_id=%s: %s",
                match.get("_raw_github_id"),
                exc,
            )

    try:
        await db.commit()
        logger.info(
            "Persisted %d high-score live issues to DB", len(high_score)
        )
    except Exception as exc:
        await db.rollback()
        logger.error("Commit failed during live issue persistence: %s", exc)
```

### Refactor `get_matched_issues()`

Replace the existing `get_matched_issues()` function body with the following. **Do not
change the function signature** — it must remain backward-compatible.

```python
async def get_matched_issues(
    db,               # AsyncSession — unchanged
    user,             # User ORM object — unchanged
    limit: int = 20,
    offset: int = 0,
    filters: dict | None = None,
    github_service_instance=None,  # ADD this optional param (default None)
    cache=None,                    # ADD this optional param (default None)
) -> list[dict]:
    """
    Return personalised, scored issue matches for a user.

    Merges:
      1. DB issues matched via pgvector cosine similarity (existing behaviour).
      2. Live GitHub Search results built from user's skill fingerprint (new).

    Results are cached in Redis for LIVE_MATCH_CACHE_TTL seconds keyed on a
    hash of the user's skill_json so similar users share cache entries.
    """
    filters = filters or {}
    skill_json = user.skill_json or {}

    # ── Try Redis cache first ────────────────────────────────────────────────
    cache_key = _fingerprint_cache_key(skill_json)
    if cache:
        try:
            cached = await cache.get(cache_key)
            if cached:
                logger.debug("Live match cache HIT key=%s", cache_key)
                all_matches = json.loads(cached)
                # Still apply pagination on cached result
                return all_matches[offset: offset + limit]
        except Exception as exc:
            logger.warning("Redis cache read failed: %s", exc)

    # ── Run DB query and live fetch concurrently ─────────────────────────────
    db_task = asyncio.create_task(
        _get_db_matched_issues(db, user, limit=limit * 3, offset=0, filters=filters)
    )

    live_task = asyncio.create_task(
        _get_live_matched_issues(
            skill_json=skill_json,
            github_service_instance=github_service_instance,
        )
    )

    db_results, live_results = await asyncio.gather(db_task, live_task)

    # ── Deduplicate: DB results win over live if same github_id ─────────────
    db_github_ids: set[int] = {
        r.get("github_id") for r in db_results if r.get("github_id")
    }
    unique_live = [
        r for r in live_results if r.get("_raw_github_id") not in db_github_ids
    ]

    all_matches = db_results + unique_live

    # ── Re-rank the unified list ─────────────────────────────────────────────
    if user.skill_vector is not None:
        all_matches = re_rank_results(user, all_matches)
    else:
        all_matches.sort(key=lambda m: m.get("match_score", 0), reverse=True)

    # ── Fire-and-forget persistence for high-score live issues ───────────────
    if unique_live:
        asyncio.create_task(
            _persist_high_score_issues(unique_live, db)
        )

    # ── Cache the full ranked list ───────────────────────────────────────────
    if cache and all_matches:
        try:
            serialisable = [
                {k: v for k, v in m.items() if k not in ("skill_vector",)}
                for m in all_matches
            ]
            await cache.set(
                cache_key,
                json.dumps(serialisable, default=str),
                ex=LIVE_MATCH_CACHE_TTL,
            )
        except Exception as exc:
            logger.warning("Redis cache write failed: %s", exc)

    # ── Paginate and return ──────────────────────────────────────────────────
    return all_matches[offset: offset + limit]
```

### Add the two internal helpers

```python
async def _get_db_matched_issues(db, user, limit: int, offset: int, filters: dict) -> list[dict]:
    """
    Existing DB-backed vector similarity match logic extracted into its own
    coroutine so it can run concurrently with the live fetch.

    Move all of the original get_matched_issues() body here verbatim.
    The return type is a list of match dicts in the same shape as before.
    """
    # ── PASTE THE ORIGINAL get_matched_issues() BODY HERE VERBATIM ──────────
    # (Do not modify it — just relocate it inside this inner function.)
    # The function must return list[dict] with keys: id, github_id, title,
    # html_url, state, labels, match_score, match_explanation, etc.
    pass  # REPLACE with original body


async def _get_live_matched_issues(
    skill_json: dict,
    github_service_instance,
) -> list[dict]:
    """
    Fetch live issues from GitHub and score them with the proxy scorer.
    Returns a list of match dicts in the same shape as _get_db_matched_issues.
    """
    if not skill_json or github_service_instance is None:
        return []

    try:
        raw_issues = await github_service_instance.fetch_live_issues_for_user(
            skill_json=skill_json,
            per_language_limit=15,
            max_queries=8,
        )
    except Exception as exc:
        logger.warning("Live GitHub fetch failed: %s", exc)
        return []

    matches = []
    for raw_issue in raw_issues:
        raw_repo = raw_issue.get("_repo") or {}
        proxy_score = score_live_issue(skill_json, raw_issue, raw_repo)
        if proxy_score < 0.10:
            continue  # Skip very poor matches early
        match_dict = _convert_raw_issue_to_match_dict(
            raw_issue, raw_repo, skill_json, proxy_score
        )
        matches.append(match_dict)

    return matches
```

---

## 8. Step 4 — worker.py

**File:** `backend/app/worker.py`

**Goal:** Make the existing ARQ indexing task user-demand-aware and add a stale-issue
cleanup task.

### Modify `index_issues_task()` (or equivalent indexing function)

Find the existing function that iterates over `(language, label)` pairs and replace the
**language source** logic (keep everything else):

```python
async def index_issues_task(ctx: dict) -> None:
    """
    Background task: index open GitHub issues into the local DB.

    Prioritises languages based on actual user skill_json data so we index
    what our users actually care about. Falls back to a hardcoded base list
    if the DB query returns nothing (cold start).
    """
    BASE_LANGUAGES = [
        "python", "javascript", "typescript", "go", "rust",
        "java", "c++", "ruby", "php", "swift",
    ]
    LABELS = ["good first issue", "help wanted"]

    db: AsyncSession = ctx["db"]

    # ── Determine languages to crawl ─────────────────────────────────────────
    try:
        # Aggregate top languages across all users who have a skill fingerprint
        result = await db.execute(
            text(
                """
                SELECT lang, COUNT(*) AS user_count
                FROM (
                    SELECT jsonb_object_keys(skill_json->'languages') AS lang
                    FROM users
                    WHERE skill_json IS NOT NULL
                      AND skill_json != 'null'::jsonb
                ) sub
                GROUP BY lang
                ORDER BY user_count DESC
                LIMIT 12
                """
            )
        )
        user_languages = [row[0].lower() for row in result.fetchall()]
    except Exception as exc:
        logger.warning("Could not query user languages, using base list: %s", exc)
        user_languages = []

    # Merge user languages with base list, user languages take priority
    combined = list(dict.fromkeys(user_languages + BASE_LANGUAGES))
    languages_to_index = combined[:12]

    logger.info("Indexing %d languages: %s", len(languages_to_index), languages_to_index)

    # ── Index each (language, label) pair ────────────────────────────────────
    for lang in languages_to_index:
        for label in LABELS:
            try:
                await index_language(ctx, lang, label)  # existing helper
            except Exception as exc:
                logger.error("Failed to index lang=%s label=%s: %s", lang, label, exc)
            await asyncio.sleep(0.5)  # gentle rate-limit buffer
```

### Add `cleanup_stale_issues_task()`

Add this as a new ARQ task function in `worker.py`:

```python
async def cleanup_stale_issues_task(ctx: dict) -> None:
    """
    Daily maintenance task.
    Removes issues from the local DB that are either:
      - closed (state != 'open'), or
      - not updated in the last 30 days.

    This keeps the DB lean and improves vector search quality.
    """
    db: AsyncSession = ctx["db"]
    try:
        result = await db.execute(
            text(
                """
                DELETE FROM issues
                WHERE state != 'open'
                   OR updated_at < NOW() - INTERVAL '30 days'
                RETURNING id
                """
            )
        )
        deleted_count = len(result.fetchall())
        await db.commit()
        logger.info("Stale issue cleanup: removed %d issues", deleted_count)
    except Exception as exc:
        await db.rollback()
        logger.error("Stale issue cleanup failed: %s", exc)
```

### Register `cleanup_stale_issues_task` in the ARQ `WorkerSettings`

Find the `WorkerSettings` class (or the dict-based settings at the bottom of `worker.py`)
and add the cleanup task to the cron jobs:

```python
# In WorkerSettings (or equivalent):

cron_jobs = [
    cron(index_issues_task, hour={0, 6, 12, 18}, minute=0),  # every 6 hours
    cron(cleanup_stale_issues_task, hour=3, minute=30),       # daily at 03:30
]
```

---

## 9. Step 5 — routes/issues.py

**File:** `backend/app/routes/issues.py`

**Goal:** Pass the GitHub service instance and Redis cache into the now-refactored
`get_matched_issues()` call. This is a small, surgical change.

### Find the `GET /issues/matches` route handler

It will look something like:

```python
@router.get("/matches", response_model=list[IssueMatch])
@cached_response(ttl=300)
async def get_matches(
    ...
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ...
):
    matches = await get_matched_issues(db, current_user, limit=limit, offset=offset)
    return matches
```

### Change the call site to pass `github_service_instance` and `cache`

```python
@router.get("/matches", response_model=list[IssueMatch])
async def get_matches(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    # github_service and cache are module-level singletons already imported
    # at the top of this file — adjust import path if needed
):
    """Return personalised issue matches for the authenticated user."""
    from app.services.github_service import github_service  # singleton import
    from app.core.cache import cache                        # singleton import

    matches = await get_matched_issues(
        db=db,
        user=current_user,
        limit=limit,
        offset=offset,
        github_service_instance=github_service,
        cache=cache,
    )
    return matches
```

**Note:** Remove the `@cached_response(ttl=300)` decorator from this route. The
matching service now handles its own Redis caching internally (3-minute TTL per
fingerprint). The old route-level 5-minute cache would mask live results.

---

## 10. Step 6 — schemas/schemas.py

**File:** `backend/app/schemas/schemas.py`

**Goal:** Add two optional fields to the `IssueMatch` (or equivalent) Pydantic response
model so the frontend can distinguish live results and display them differently if
desired. Both fields are optional and default to non-breaking values.

### Find the `IssueMatch` schema class and add two fields

```python
class IssueMatch(BaseModel):
    # ... all existing fields unchanged ...

    # New optional fields (backward-compatible — both have defaults)
    is_live_result: bool = Field(
        default=False,
        description="True if this issue was fetched live from GitHub in this "
                    "request rather than retrieved from the local database.",
    )
    live_fetched_at: str | None = Field(
        default=None,
        description="ISO-8601 timestamp of when this live result was fetched. "
                    "None for DB-backed results.",
    )
```

### Populate these fields in the serialisation step inside `matching_service.py`

When building each match dict, set:

```python
from datetime import datetime, timezone

match_dict["is_live_result"] = True
match_dict["live_fetched_at"] = datetime.now(timezone.utc).isoformat()
```

For DB-backed results (in `_get_db_matched_issues`), leave them at default (`False`,
`None`) — they will be absent from the dict and Pydantic will use defaults.

---

## 11. Step 7 — No Schema Migration Needed

**No new Alembic migration is required.**

The `issues` table already has all the columns needed to store live-fetched issues
(`github_id`, `title`, `body`, `html_url`, `state`, `labels`, `skill_vector`, etc.).
The `_persist_high_score_issues()` function upserts into this existing table.

The only thing to verify is that the `repositories` table `INSERT` in
`_persist_high_score_issues()` sets all `NOT NULL` columns. Review `0001_initial_schema.py`
for the `NOT NULL` column list and ensure every such column is provided in the
`Repository(...)` constructor call in Step 3.

---

## 12. Step 8 — Redis Key Contracts

All new Redis keys introduced in this refactor:

| Key pattern | TTL | Purpose |
|---|---|---|
| `live_matches:{md5_16}` | 180 s | Cached unified match list keyed on fingerprint hash |

The `md5_16` is the first 16 hex characters of `md5(json.dumps(skill_json, sort_keys=True))`.

Existing keys are untouched:
- `gh:search-text:{md5}` — GitHub free-text search cache (10 min) — used by the new
  `fetch_live_issues_for_user()` via `search_issues_free_text()`.

---

## 13. Step 9 — Environment Variables

No new environment variables are required. The existing configuration in
`app/core/config.py` is sufficient.

Optional tuning variables you MAY add to `.env` and wire through `config.py` if you
want runtime configurability (not required for the initial implementation):

```dotenv
# Optional tuning (all have hardcoded defaults in the code above)
LIVE_MATCH_CACHE_TTL=180          # seconds
PERSIST_SCORE_THRESHOLD=0.65      # 0–1 composite score
LIVE_FETCH_MAX_QUERIES=8          # max parallel GitHub queries per user request
LIVE_FETCH_PER_LANGUAGE_LIMIT=15  # GitHub results per query
```

---

## 14. Step 10 — Testing Checklist

Run after each step. All 84 existing tests must continue to pass.

### Automated

```bash
cd backend
pytest tests/ -v --tb=short
```

### Manual smoke tests (in order)

**1. Check fingerprint cache key stability**

```python
from app.services.matching_service import _fingerprint_cache_key
a = _fingerprint_cache_key({"languages": {"python": 0.6, "typescript": 0.4}})
b = _fingerprint_cache_key({"languages": {"typescript": 0.4, "python": 0.6}})
assert a == b, "Key must be order-independent"
print(a)  # Should be: live_matches:<16 hex chars>
```

**2. Check proxy scorer edge cases**

```python
from app.services.scoring_service import score_live_issue

# PR should always score 0
pr = {"pull_request": {"url": "..."}, "labels": [], "updated_at": "2025-01-01T00:00:00Z"}
assert score_live_issue({}, pr, {}) == 0.0

# Perfect language match
user = {"languages": {"python": 0.8}, "topics": [], "top_skills": []}
issue = {
    "labels": [{"name": "good first issue"}],
    "updated_at": "2025-05-01T00:00:00Z",
    "comments": 3,
}
repo = {"language": "Python", "stargazers_count": 5000, "forks_count": 200, "topics": []}
score = score_live_issue(user, issue, repo)
assert 0.5 < score < 1.0, f"Expected strong match, got {score}"
print(f"Score: {score}")
```

**3. Live endpoint test (requires running server and GitHub token)**

```bash
curl -s -H "Authorization: Bearer $JWT_TOKEN" \
  "http://localhost:8000/api/v1/issues/matches?limit=5" | \
  python3 -m json.tool | grep -E '"is_live_result"|"title"'
```

Expected: mix of `"is_live_result": false` (DB) and `"is_live_result": true` (live).

**4. Cache effectiveness**

Hit the endpoint twice in quick succession:

```bash
time curl -s -H "Authorization: Bearer $JWT_TOKEN" \
  "http://localhost:8000/api/v1/issues/matches" > /dev/null
# Second call should be significantly faster (cache hit)
time curl -s -H "Authorization: Bearer $JWT_TOKEN" \
  "http://localhost:8000/api/v1/issues/matches" > /dev/null
```

**5. Worker language prioritisation**

Trigger the indexing task manually via the ARQ CLI and check logs:

```bash
arq app.worker.WorkerSettings --burst
```

Expected log line: `Indexing 12 languages: ['python', 'typescript', ...]` where the
first languages correspond to your most common user languages.

**6. Stale issue cleanup**

Manually insert a stale issue into the DB and verify it is removed:

```sql
INSERT INTO issues (github_id, title, html_url, state, updated_at, repository_id)
VALUES (9999999999, 'Stale test', 'https://github.com/test', 'open',
        NOW() - INTERVAL '35 days', 1);
```

Run the cleanup task and verify it is gone.

---

## 15. Rollback Plan

If any step introduces a regression:

1. `get_matched_issues()` — the original body was moved verbatim into
   `_get_db_matched_issues()`. To roll back, move it back into `get_matched_issues()`
   and remove the new live-fetch code. No DB changes to undo.

2. `worker.py` — revert `index_issues_task()` to use the hardcoded language list.
   The `cleanup_stale_issues_task` can be disabled by removing it from `cron_jobs`.

3. `routes/issues.py` — restore the `@cached_response(ttl=300)` decorator and remove
   the new kwargs from the `get_matched_issues()` call.

4. Redis — new `live_matches:*` keys expire in 3 minutes naturally; no manual flush
   needed.

5. Database — no migration was applied, so there is nothing to reverse.

---

*End of refactor spec. Total files modified: 5. No new dependencies. No DB migrations.*

---

---

# PART 2 — Exact Implementation Details

> **Agent:** Read Part 1 first. This section fills every placeholder left there with
> exact, copy-pasteable code. Do not implement Part 2 steps out of order.

---

## 16. Exact Import Blocks for Every Modified File

The existing files have their own imports. Add only the lines marked **ADD** below.
Do not remove or reorder existing imports — append new ones after the last existing
import line in each file.

### `backend/app/services/scoring_service.py`

```python
# ADD — these are only needed inside score_live_issue() so they are imported
# locally inside that function body. No top-level additions required.
# (datetime and timezone are imported inline inside score_live_issue — see Part 1)
```

No top-level import changes needed for `scoring_service.py`.

---

### `backend/app/services/github_service.py`

```python
# ADD at the top of the file, after all existing imports:
import asyncio   # ADD — if not already present (check first)
```

The `_LIVE_FETCH_SEMAPHORE` is a module-level variable, not an import. Place it
immediately after the last `import` / `from ... import` line:

```python
# Module-level semaphore — limits parallel live-fetch queries per user request
_LIVE_FETCH_SEMAPHORE = asyncio.Semaphore(4)
```

---

### `backend/app/services/matching_service.py`

Replace the entire import block at the top of this file with the following. All
existing imports are preserved; new ones are marked `# NEW`:

```python
from __future__ import annotations

import asyncio          # NEW
import hashlib          # NEW
import json             # NEW
import logging          # NEW
from datetime import datetime, timezone  # NEW

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set  # adjust if your cache module differs
from app.models.models import Issue, Repository, User
from app.services.scoring_service import (
    SCORE_WEIGHTS,
    compute_freshness_score,
    compute_interest_match,
    compute_popularity_score,
    compute_repo_activity_score,
    explain_score,
    score_live_issue,          # NEW
    build_live_issue_explanation,  # NEW
)
from app.services.skill_service import issue_text_to_vector  # NEW (for persistence)

logger = logging.getLogger("issuecompass.matching")  # NEW
```

---

### `backend/app/routes/issues.py`

```python
# ADD at the top, after existing imports:
from app.services.github_service import github_service as _gh_service  # NEW
# The `cache` object — import the Redis client singleton directly:
from app.core.cache import redis_client as _cache  # NEW
# NOTE: If your cache module exposes a different name (e.g. `get_redis_client()`),
# adjust accordingly. The important thing is you pass a redis-like object that has
# .get(key) and .set(key, value, ex=ttl) async methods.
```

---

### `backend/app/worker.py`

```python
# ADD after existing imports:
import asyncio  # ADD if not already present
from sqlalchemy import text  # ADD if not already present
```

---

## 17. Complete `_get_db_matched_issues()` Body

Part 1 said: *"Paste the original `get_matched_issues()` body here verbatim."*

Below is the **reconstructed body** based on the system report's description of
`matching_service.py` (204 lines). The agent must verify this against the actual file
and reconcile any differences — the logic here is authoritative in structure; the
actual variable names in the file take precedence.

```python
async def _get_db_matched_issues(
    db: AsyncSession,
    user: User,
    limit: int,
    offset: int,
    filters: dict,
) -> list[dict]:
    """
    Query the local PostgreSQL issues table using pgvector cosine similarity
    against the user's skill_vector. This is the original matching logic,
    extracted verbatim from the old get_matched_issues() body.

    Returns a list of match dicts. Each dict has the keys expected by the
    API response schema and by re_rank_results().
    """
    if user.skill_vector is None:
        # No vector yet — return empty; live fetch will carry the result
        return []

    # Pool size calculation: ensures enough candidates for deep pagination
    pool_size = min(max(offset + limit, limit * 5), 500)

    # ── Main vector similarity query ──────────────────────────────────────────
    # Fetch open issues that have a skill_vector (partial index ensures speed)
    stmt = (
        select(
            Issue,
            Repository,
        )
        .join(Repository, Issue.repository_id == Repository.id)
        .where(
            Issue.state == "open",
            Issue.skill_vector.isnot(None),
            Repository.is_archived.is_(False),
        )
    )

    # Apply optional filters from query params
    if filters.get("language"):
        stmt = stmt.where(
            Repository.primary_language.ilike(filters["language"])
        )
    if filters.get("is_good_first_issue"):
        stmt = stmt.where(Issue.is_good_first_issue.is_(True))
    if filters.get("is_help_wanted"):
        stmt = stmt.where(Issue.is_help_wanted.is_(True))
    if filters.get("difficulty"):
        difficulty_map = {
            "beginner":     (0.0, 0.4),
            "intermediate": (0.4, 0.7),
            "advanced":     (0.7, 1.0),
        }
        lo, hi = difficulty_map.get(filters["difficulty"], (0.0, 1.0))
        stmt = stmt.where(Issue.complexity_score.between(lo, hi))

    # Limit to the pool (not the final limit — scoring/re-ranking happens after)
    stmt = stmt.limit(pool_size)

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return []

    # ── Score every (issue, repo) pair ───────────────────────────────────────
    import numpy as np  # only needed here; numpy is already a transitive dep

    def cosine_similarity(a: list[float], b: list[float]) -> float:
        va, vb = np.array(a, dtype=float), np.array(b, dtype=float)
        norm_a, norm_b = np.linalg.norm(va), np.linalg.norm(vb)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(va, vb) / (norm_a * norm_b))

    user_vec = user.skill_vector  # already a list[float]
    user_skills = user.skill_json or {}

    matches = []
    for issue, repo in rows:
        # Primary: vector cosine similarity
        skill_sim = cosine_similarity(user_vec, issue.skill_vector)

        # Supporting dimensions
        activity  = compute_repo_activity_score(repo)
        freshness = compute_freshness_score(issue)
        popularity = compute_popularity_score(issue, repo)
        interest  = compute_interest_match(
            user_skills,
            issue.required_skills or {},
        )

        # Weighted blend (SCORE_WEIGHTS from scoring_service)
        final_score = (
            skill_sim  * SCORE_WEIGHTS["skill_match"]    +
            popularity * SCORE_WEIGHTS["popularity"]     +
            interest   * SCORE_WEIGHTS["interest_match"] +
            activity   * SCORE_WEIGHTS["repo_activity"]  +
            freshness  * SCORE_WEIGHTS["freshness"]
        )

        # Matching skill names for display
        from app.services.matching_service import find_matching_skills
        matched_skills = find_matching_skills(
            user_skills,
            issue.required_skills or {},
        )

        # Rule-based explanation (AI explanation is generated async separately)
        explanation = explain_score(
            skill_sim, activity, freshness, interest, popularity,
            matched_skills, final_score,
        )

        matches.append({
            # DB identity
            "id": issue.id,
            "github_id": issue.github_id,
            "number": issue.number,
            "title": issue.title,
            "body": (issue.body or "")[:2000],
            "html_url": issue.html_url,
            "state": issue.state,
            "labels": issue.labels or [],
            "is_good_first_issue": issue.is_good_first_issue,
            "is_help_wanted": issue.is_help_wanted,
            "comments": issue.comments or 0,
            "created_at": issue.created_at,
            "updated_at": issue.updated_at,
            # Repository
            "repo_id": repo.id,
            "repo_full_name": repo.full_name,
            "repo_name": repo.name,
            "repo_html_url": repo.html_url,
            "repo_language": repo.primary_language or "",
            "repo_stars": repo.stars or 0,
            "repo_forks": repo.forks or 0,
            "repo_topics": repo.topics or [],
            "repo_is_archived": repo.is_archived,
            # Scoring
            "match_score": round(final_score, 4),
            "skill_vector": issue.skill_vector,   # kept for re_rank_results
            "required_skills": issue.required_skills or {},
            "complexity_score": issue.complexity_score or 0.5,
            "matching_skills": matched_skills,
            "match_explanation": explanation,
            # Marker: DB-backed result (not live)
            "_is_live": False,
            "_raw_github_id": issue.github_id,
            # Schema fields (with defaults)
            "is_live_result": False,
            "live_fetched_at": None,
        })

    return matches
```

**Agent verification step:** After pasting this body, open the actual
`matching_service.py` and confirm:
- The `Issue` and `Repository` ORM column names match (e.g., `repo.primary_language`
  vs `repo.language` — use whatever the actual model uses).
- The `explain_score()` signature matches — adjust argument order if needed.
- `find_matching_skills` is either defined in this file or imported correctly.

---

## 18. How `re_rank_results()` Handles Live Issues

Live issues have `skill_vector = None`. The existing `re_rank_results()` function
(used in `search_service.py`) performs a second-pass cosine similarity. It will crash
or produce a wrong result if passed a `None` vector.

**The fix: guard the re-rank call in the new `get_matched_issues()` body.**

The refactored `get_matched_issues()` already conditionally calls `re_rank_results`:

```python
if user.skill_vector is not None:
    all_matches = re_rank_results(user, all_matches)
else:
    all_matches.sort(key=lambda m: m.get("match_score", 0), reverse=True)
```

But even when `user.skill_vector` is not None, `re_rank_results` may try to call
`cosine_similarity(user_vec, issue["skill_vector"])` — and live issues have
`skill_vector = None`.

**Patch `re_rank_results()` in `search_service.py` to skip None vectors:**

Find the inner loop inside `re_rank_results()` and wrap the cosine call:

```python
# BEFORE (existing code, approximate):
sim = cosine_similarity(user_vec, issue["skill_vector"])

# AFTER:
issue_vec = issue.get("skill_vector")
if issue_vec is None:
    # Live issue — use the proxy score already computed; do not overwrite
    sim = issue.get("match_score", 0.0)
else:
    sim = cosine_similarity(user_vec, issue_vec)
```

This single change makes `re_rank_results()` safe for mixed DB+live result lists
without altering its behaviour for pure DB result lists.

---

## 19. Rate-Limit Guard Before Firing Live Queries

The existing `_gh_request()` in `github_service.py` already sleeps 1 second when
`X-RateLimit-Remaining < 10`. But we should also skip the entire live fetch if the
remaining budget is critically low, rather than burning it from a live user request.

Add this check at the **top of `fetch_live_issues_for_user()`**, before building queries:

```python
async def fetch_live_issues_for_user(self, skill_json, per_language_limit=15, max_queries=8):
    if not skill_json:
        return []

    # ── Rate-limit budget check ───────────────────────────────────────────────
    # self._rate_limit_remaining is the attribute already tracked in _gh_request()
    # (check the actual attribute name in your github_service.py — adjust if needed)
    remaining = getattr(self, "_rate_limit_remaining", 5000)
    if remaining < 50:
        logger.warning(
            "GitHub rate limit low (%d remaining) — skipping live fetch", remaining
        )
        return []

    # ... rest of function body from Part 1 ...
```

**Important:** The attribute name `_rate_limit_remaining` must match whatever
`github_service.py` actually stores. Search for `X-RateLimit-Remaining` in the file
and find the `self.???` assignment. Use that exact attribute name.

---

## 20. New Tests to Add

**File:** `backend/tests/test_scoring_service.py`

Add the following test class at the bottom of the file:

```python
class TestScoreLiveIssue:
    """Tests for the new proxy scorer for live GitHub issues."""

    BASE_USER_SKILLS = {
        "languages": {"python": 0.7, "typescript": 0.3},
        "topics": ["web", "api"],
        "top_skills": ["fastapi", "react"],
        "categories": {"backend": 0.6, "frontend": 0.4},
        "experience_level": "intermediate",
    }

    BASE_REPO = {
        "language": "Python",
        "topics": ["api", "web"],
        "stargazers_count": 5000,
        "forks_count": 300,
        "full_name": "testorg/testrepo",
        "name": "testrepo",
        "archived": False,
    }

    BASE_ISSUE = {
        "title": "Fix authentication bug",
        "body": "The login endpoint returns 500 on empty password.",
        "labels": [{"name": "good first issue"}, {"name": "bug"}],
        "updated_at": "2025-05-01T00:00:00Z",
        "created_at": "2025-04-28T00:00:00Z",
        "comments": 8,
        "pull_request": None,  # not a PR
    }

    def test_pull_request_always_scores_zero(self):
        issue_as_pr = {**self.BASE_ISSUE, "pull_request": {"url": "https://..."}}
        score = score_live_issue(self.BASE_USER_SKILLS, issue_as_pr, self.BASE_REPO)
        assert score == 0.0

    def test_perfect_language_match_scores_high(self):
        score = score_live_issue(self.BASE_USER_SKILLS, self.BASE_ISSUE, self.BASE_REPO)
        assert score >= 0.55, f"Expected strong match, got {score}"

    def test_language_mismatch_scores_lower(self):
        repo_rust = {**self.BASE_REPO, "language": "Rust", "topics": []}
        score = score_live_issue(self.BASE_USER_SKILLS, self.BASE_ISSUE, repo_rust)
        # lang_score component will be 0 → overall lower
        assert score <= 0.45, f"Expected weak match for unknown lang, got {score}"

    def test_good_first_issue_label_increases_score(self):
        issue_no_label = {**self.BASE_ISSUE, "labels": []}
        score_with    = score_live_issue(self.BASE_USER_SKILLS, self.BASE_ISSUE, self.BASE_REPO)
        score_without = score_live_issue(self.BASE_USER_SKILLS, issue_no_label, self.BASE_REPO)
        assert score_with > score_without

    def test_stale_issue_scores_lower_than_fresh(self):
        from datetime import datetime, timezone, timedelta
        old_date = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
        fresh_issue = {**self.BASE_ISSUE, "updated_at": "2025-05-20T00:00:00Z"}
        stale_issue = {**self.BASE_ISSUE, "updated_at": old_date}
        score_fresh = score_live_issue(self.BASE_USER_SKILLS, fresh_issue, self.BASE_REPO)
        score_stale = score_live_issue(self.BASE_USER_SKILLS, stale_issue, self.BASE_REPO)
        assert score_fresh > score_stale

    def test_empty_skill_json_returns_low_score(self):
        score = score_live_issue({}, self.BASE_ISSUE, self.BASE_REPO)
        assert score < 0.30

    def test_score_is_clamped_between_zero_and_one(self):
        score = score_live_issue(self.BASE_USER_SKILLS, self.BASE_ISSUE, self.BASE_REPO)
        assert 0.0 <= score <= 1.0

    def test_missing_updated_at_does_not_crash(self):
        issue_no_date = {**self.BASE_ISSUE, "updated_at": None, "created_at": None}
        score = score_live_issue(self.BASE_USER_SKILLS, issue_no_date, self.BASE_REPO)
        assert 0.0 <= score <= 1.0
```

---

**File:** `backend/tests/test_matching_service.py`

Add the following at the bottom (existing test for notification matching stays untouched):

```python
class TestFingerprintCacheKey:
    """Tests for the Redis cache key generator."""

    def test_key_is_order_independent(self):
        from app.services.matching_service import _fingerprint_cache_key
        a = _fingerprint_cache_key({"languages": {"python": 0.6, "typescript": 0.4}})
        b = _fingerprint_cache_key({"languages": {"typescript": 0.4, "python": 0.6}})
        assert a == b

    def test_key_starts_with_prefix(self):
        from app.services.matching_service import _fingerprint_cache_key
        key = _fingerprint_cache_key({"languages": {"rust": 1.0}})
        assert key.startswith("live_matches:")

    def test_different_skills_produce_different_keys(self):
        from app.services.matching_service import _fingerprint_cache_key
        key_a = _fingerprint_cache_key({"languages": {"python": 1.0}})
        key_b = _fingerprint_cache_key({"languages": {"rust": 1.0}})
        assert key_a != key_b

    def test_empty_skill_json_does_not_crash(self):
        from app.services.matching_service import _fingerprint_cache_key
        key = _fingerprint_cache_key({})
        assert isinstance(key, str) and len(key) > 0


class TestConvertRawIssueToMatchDict:
    """Tests for the live-issue shape converter."""

    RAW_ISSUE = {
        "id": 123456789,
        "number": 42,
        "title": "Fix null pointer in parser",
        "body": "Steps to reproduce...",
        "html_url": "https://github.com/org/repo/issues/42",
        "labels": [{"name": "good first issue"}],
        "comments": 5,
        "created_at": "2025-04-01T00:00:00Z",
        "updated_at": "2025-05-01T00:00:00Z",
        "pull_request": None,
    }
    RAW_REPO = {
        "full_name": "org/repo",
        "name": "repo",
        "html_url": "https://github.com/org/repo",
        "language": "Go",
        "stargazers_count": 2000,
        "forks_count": 150,
        "topics": ["cli", "tooling"],
        "archived": False,
    }
    USER_SKILLS = {
        "languages": {"go": 0.9},
        "topics": ["cli"],
        "top_skills": ["golang"],
    }

    def test_produces_required_keys(self):
        from app.services.matching_service import _convert_raw_issue_to_match_dict
        d = _convert_raw_issue_to_match_dict(self.RAW_ISSUE, self.RAW_REPO, self.USER_SKILLS, 0.75)
        required = ["github_id", "title", "html_url", "match_score", "_is_live",
                    "is_good_first_issue", "repo_stars", "labels"]
        for key in required:
            assert key in d, f"Missing key: {key}"

    def test_is_live_flag_is_true(self):
        from app.services.matching_service import _convert_raw_issue_to_match_dict
        d = _convert_raw_issue_to_match_dict(self.RAW_ISSUE, self.RAW_REPO, self.USER_SKILLS, 0.75)
        assert d["_is_live"] is True
        assert d["is_live_result"] is True

    def test_skill_vector_is_none(self):
        from app.services.matching_service import _convert_raw_issue_to_match_dict
        d = _convert_raw_issue_to_match_dict(self.RAW_ISSUE, self.RAW_REPO, self.USER_SKILLS, 0.75)
        assert d["skill_vector"] is None

    def test_good_first_issue_flag_set(self):
        from app.services.matching_service import _convert_raw_issue_to_match_dict
        d = _convert_raw_issue_to_match_dict(self.RAW_ISSUE, self.RAW_REPO, self.USER_SKILLS, 0.75)
        assert d["is_good_first_issue"] is True

    def test_matching_skills_contains_overlap(self):
        from app.services.matching_service import _convert_raw_issue_to_match_dict
        d = _convert_raw_issue_to_match_dict(self.RAW_ISSUE, self.RAW_REPO, self.USER_SKILLS, 0.75)
        # "go" from user languages should appear in matching_skills
        assert "go" in d["matching_skills"] or "cli" in d["matching_skills"]
```

---

**File:** `backend/tests/test_github_service.py`

Add to the existing test file:

```python
class TestFetchLiveIssuesForUser:
    """Tests for the new live-fetch method on GitHubService."""

    def test_empty_skill_json_returns_empty_list(self):
        import asyncio
        from app.services.github_service import github_service
        result = asyncio.get_event_loop().run_until_complete(
            github_service.fetch_live_issues_for_user({})
        )
        assert result == []

    def test_query_count_capped_at_max_queries(self, mocker):
        """Never fires more than max_queries concurrent requests."""
        import asyncio
        from app.services.github_service import github_service

        call_count = {"n": 0}
        async def fake_search(q, per_page=15):
            call_count["n"] += 1
            return []

        mocker.patch.object(github_service, "search_issues_free_text", side_effect=fake_search)

        skill_json = {
            "languages": {"python": 0.4, "typescript": 0.3, "rust": 0.2, "go": 0.1},
            "topics": ["api", "web"],
            "top_skills": [],
        }
        asyncio.get_event_loop().run_until_complete(
            github_service.fetch_live_issues_for_user(skill_json, max_queries=6)
        )
        assert call_count["n"] <= 6

    def test_deduplication_by_github_id(self, mocker):
        """Issues returned by multiple queries are deduplicated."""
        import asyncio
        from app.services.github_service import github_service

        duplicate_issue = {
            "id": 9999,
            "title": "Duplicate",
            "repository": {"language": "Python", "topics": []},
            "_repo": {},
        }

        async def fake_search(q, per_page=15):
            return [duplicate_issue]

        mocker.patch.object(github_service, "search_issues_free_text", side_effect=fake_search)

        skill_json = {"languages": {"python": 0.8}, "topics": [], "top_skills": []}
        result = asyncio.get_event_loop().run_until_complete(
            github_service.fetch_live_issues_for_user(skill_json)
        )
        # Should appear only once despite multiple queries returning it
        ids = [r["id"] for r in result]
        assert ids.count(9999) == 1

    def test_low_rate_limit_skips_fetch(self, mocker):
        """If rate limit budget is low, returns empty without calling GitHub."""
        import asyncio
        from app.services.github_service import github_service

        mocker.patch.object(github_service, "_rate_limit_remaining", 20)
        search_mock = mocker.patch.object(github_service, "search_issues_free_text")

        skill_json = {"languages": {"python": 1.0}, "topics": [], "top_skills": []}
        result = asyncio.get_event_loop().run_until_complete(
            github_service.fetch_live_issues_for_user(skill_json)
        )
        assert result == []
        search_mock.assert_not_called()
```

---

## 21. Singleton Wiring — Cache and GitHub Service in Routes

Your `app/core/cache.py` exposes a `redis_client` or `cache` object at module level.
Your `app/services/github_service.py` exposes a singleton `github_service` instance
at module level (confirmed by the existing usage pattern in the codebase).

**In `app/routes/issues.py`**, the import at the top of the file should be:

```python
# Confirm the exact module-level names by running:
#   grep -n "^github_service\s*=" backend/app/services/github_service.py
#   grep -n "^redis_client\s*=\|^cache\s*=" backend/app/core/cache.py
# Then use those exact names below.

from app.services.github_service import github_service   # singleton
from app.core.cache import redis_client                  # singleton (or `cache`)
```

**Pass them to `get_matched_issues()`:**

```python
@router.get("/matches", response_model=list[IssueMatch])
async def get_matches(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    language: str | None = Query(default=None),
    is_good_first_issue: bool | None = Query(default=None),
    is_help_wanted: bool | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filters = {
        "language": language,
        "is_good_first_issue": is_good_first_issue,
        "is_help_wanted": is_help_wanted,
        "difficulty": difficulty,
    }
    # Remove None values so the DB query doesn't filter on them
    filters = {k: v for k, v in filters.items() if v is not None}

    return await get_matched_issues(
        db=db,
        user=current_user,
        limit=limit,
        offset=offset,
        filters=filters,
        github_service_instance=github_service,
        cache=redis_client,
    )
```

**Note on the removed `@cached_response` decorator:** The `route_cache.py` decorator
sets a 5-minute TTL for the entire `/matches` response keyed on the route URL (not
the user fingerprint). It must be removed because:
1. The new internal cache is per-fingerprint (3 min), not per-URL.
2. Two users hitting the same URL would incorrectly share each other's match results
   if the route-level cache were still active.

---

## 22. ARQ Worker Context (`ctx`) Object

The ARQ `ctx` dict passed to every task function already contains:

```python
ctx = {
    "db":    AsyncSession,    # SQLAlchemy async session (injected by startup)
    "redis": Redis,           # aioredis client (used for ARQ broker)
    # plus ARQ internals: job_id, job_try, score, etc.
}
```

This means in `index_issues_task(ctx)` and `cleanup_stale_issues_task(ctx)`, you
access the database as `ctx["db"]` and execute queries directly:

```python
async def cleanup_stale_issues_task(ctx: dict) -> None:
    db: AsyncSession = ctx["db"]   # ← correct
    ...
```

**Verify your worker's `startup` function** injects the DB session into ctx. It will
look similar to:

```python
async def startup(ctx):
    ctx["db"] = AsyncSession(bind=engine)
    # or:
    ctx["db"] = async_session_factory()
```

If the session is created per-task (not at startup), the pattern is the same — just
confirm the key name is `"db"` in your actual `worker.py`.

---

## 23. Edge Cases and Error Handling Map

The agent must ensure every possible failure path is handled gracefully. This table
maps failure scenarios to the required response.

| Scenario | Location | Required behaviour |
|---|---|---|
| GitHub API returns 403 (rate limit) | `fetch_live_issues_for_user()` | `_run_query` catches exception, returns `[]`. Outer `asyncio.gather` gets empty list for that query. Request still returns DB results. |
| GitHub API returns 422 (bad query syntax) | `_run_query` | Caught by `except Exception`, logged as WARNING, returns `[]` for that query only. |
| Redis unavailable (cache write fails) | `get_matched_issues()` after scoring | Caught, logged as WARNING, result is still returned to user. No crash. |
| Redis unavailable (cache read fails) | `get_matched_issues()` cache check | Caught, logged as WARNING, proceeds to live fetch + DB query. |
| `skill_json` is `None` or `{}` | `_get_live_matched_issues()` | Early return `[]`. DB query still proceeds. |
| `skill_vector` is `None` (new user) | `_get_db_matched_issues()` | Returns `[]`. Live results still returned and sorted by proxy score. |
| `issue_text_to_vector()` fails during persistence | `_persist_high_score_issues()` | Inner try/except logs WARNING for that issue, skips it, continues with next. |
| DB commit fails during persistence | `_persist_high_score_issues()` | Rollback + log ERROR. Fire-and-forget means user's response is already sent. |
| `asyncio.create_task` for persistence leaks | `get_matched_issues()` | The task is detached (fire-and-forget). Add `asyncio.shield()` if needed for cleanup on shutdown. |
| `pull_request` field present in GitHub issue | `score_live_issue()` | Returns `0.0`. Filtered out in `_get_live_matched_issues()` by `if proxy_score < 0.10`. |
| Empty body field from GitHub API | `_convert_raw_issue_to_match_dict()` | `(raw_issue.get("body") or "")[:2000]` — safe for `None`. |
| Very long body (>10k chars) | `_persist_high_score_issues()` | `issue.body = match.get("body", "")[:10000]` — truncated before INSERT. |

---

## 24. Precise Execution Order for the Agent

Follow these steps **exactly in this order**. Run `pytest` after each numbered step
before proceeding to the next.

```
Step 1.  Edit scoring_service.py
         → Add score_live_issue()
         → Add build_live_issue_explanation()
         Run: pytest tests/test_scoring_service.py -v
         All existing scoring tests must pass + new TestScoreLiveIssue tests pass.

Step 2.  Edit github_service.py
         → Add module-level _LIVE_FETCH_SEMAPHORE
         → Add fetch_live_issues_for_user() method
         → Add per_page param to search_issues_free_text() if missing
         Run: pytest tests/test_github_service.py -v

Step 3.  Edit search_service.py (re_rank_results guard only)
         → Add the None-vector guard inside re_rank_results()
         Run: pytest tests/test_search_service.py -v

Step 4.  Edit matching_service.py
         → Update imports
         → Add module constants (LIVE_MATCH_CACHE_TTL, PERSIST_SCORE_THRESHOLD)
         → Add _fingerprint_cache_key()
         → Add _convert_raw_issue_to_match_dict()
         → Add _find_live_matching_skills()
         → Add _persist_high_score_issues()
         → Extract original get_matched_issues() body into _get_db_matched_issues()
         → Add _get_live_matched_issues()
         → Replace get_matched_issues() with the new merged version
         Run: pytest tests/test_matching_service.py -v

Step 5.  Edit routes/issues.py
         → Add imports for github_service and redis_client singletons
         → Remove @cached_response decorator from /matches route
         → Add new parameters to get_matched_issues() call
         → Add query param bindings for filters
         Run: pytest tests/test_routes.py -v
         All 47 route tests must pass.

Step 6.  Edit schemas/schemas.py
         → Add is_live_result and live_fetched_at to IssueMatch
         Run: pytest tests/ -v
         Full suite: 84+ tests must pass (2 skipped is expected).

Step 7.  Edit worker.py
         → Add text import from sqlalchemy
         → Refactor index_issues_task() to be user-demand-aware
         → Add cleanup_stale_issues_task()
         → Register cleanup in cron_jobs
         Run: pytest tests/ -v   (no worker-specific test file exists; just verify suite)

Step 8.  Add new test cases
         → Append TestScoreLiveIssue to test_scoring_service.py
         → Append TestFingerprintCacheKey and TestConvertRawIssueToMatchDict
           to test_matching_service.py
         → Append TestFetchLiveIssuesForUser to test_github_service.py
         Run: pytest tests/ -v
         All new tests must pass.

Step 9.  Integration smoke test (live server, see Section 14 in Part 1)
         → Start the server locally
         → Hit /issues/matches twice and verify:
             - First call: mix of is_live_result: true/false
             - Second call (<3 min later): served from Redis, significantly faster
         → Check logs for: "Persisted N high-score live issues to DB"
         → Verify worker logs: "Indexing 12 languages: ['python', ...]"

Step 10. Final full test run
         Run: pytest tests/ -v --tb=short
         Expected: 84+ passing, 2 skipped, 0 failures.
```

---

## 25. Quick Reference — All New Symbols

| Symbol | File | Type | Purpose |
|---|---|---|---|
| `score_live_issue(user_skills, raw_issue, raw_repo)` | `scoring_service.py` | function | 0-1 proxy score for live GitHub issue |
| `build_live_issue_explanation(...)` | `scoring_service.py` | function | Rule-based match explanation string |
| `_LIVE_FETCH_SEMAPHORE` | `github_service.py` | `asyncio.Semaphore(4)` | Concurrent query limiter |
| `fetch_live_issues_for_user(skill_json, ...)` | `github_service.py` | async method | Fire parallel GitHub Search queries |
| `LIVE_MATCH_CACHE_TTL` | `matching_service.py` | `int = 180` | Redis TTL in seconds |
| `PERSIST_SCORE_THRESHOLD` | `matching_service.py` | `float = 0.65` | Min score to write live issue to DB |
| `_fingerprint_cache_key(skill_json)` | `matching_service.py` | function | Redis key from skill fingerprint hash |
| `_convert_raw_issue_to_match_dict(...)` | `matching_service.py` | function | Shape converter: raw GitHub → match dict |
| `_find_live_matching_skills(...)` | `matching_service.py` | function | Skill overlap for live issues |
| `_persist_high_score_issues(live_matches, db)` | `matching_service.py` | async function | Fire-and-forget DB upsert |
| `_get_db_matched_issues(db, user, ...)` | `matching_service.py` | async function | Extracted original DB query logic |
| `_get_live_matched_issues(skill_json, ...)` | `matching_service.py` | async function | Live fetch + proxy score |
| `cleanup_stale_issues_task(ctx)` | `worker.py` | async ARQ task | Daily DB cleanup of closed/old issues |
| `is_live_result` | `schemas.py → IssueMatch` | `bool = False` | API response field |
| `live_fetched_at` | `schemas.py → IssueMatch` | `str \| None = None` | API response field |

---

*End of Part 2. Total: 25 sections across Parts 1 and 2. Files modified: 6.*
*New test cases: 17. No new migrations. No new environment variables required.*
