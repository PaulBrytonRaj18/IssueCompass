from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set
from app.models.models import Issue, Repository, User
from app.services.scoring_service import (
    SCORE_WEIGHTS,
    build_live_issue_explanation,
    compute_freshness_score,
    compute_interest_match,
    compute_popularity_score,
    compute_repo_activity_score,
    safe_explain_score,
    score_live_issue,
)
from app.services.skill_service import _stable_hash, issue_text_to_vector

logger = logging.getLogger("issuecompass.matching")

# Redis TTL for live-match cache (seconds)
LIVE_MATCH_CACHE_TTL = 180  # 3 minutes

# Minimum composite score for a live issue to be persisted to PostgreSQL
PERSIST_SCORE_THRESHOLD = 0.65


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def find_matching_skills(
    user_skills: Dict[str, Any],
    issue_skills: Dict[str, Any],
) -> List[str]:
    user_langs = set(user_skills.get("languages", {}).keys())
    user_topics = set(user_skills.get("topics", []))
    user_top = set(user_skills.get("top_skills", []))

    issue_cats = issue_skills.get("categories", {})
    matching = set()
    for cat_skills in issue_cats.values():
        for skill in cat_skills:
            if skill in user_langs or skill in user_topics or skill in user_top:
                matching.add(skill)
    return list(matching)[:5]


def _fingerprint_cache_key(skill_json: dict) -> str:
    """
    Deterministic Redis key for a user's live match results.
    Keyed on a hash of skill_json so two users with identical fingerprints
    share the same cached results (saves GitHub API quota).
    """
    canonical = json.dumps(skill_json, sort_keys=True, separators=(",", ":"))
    digest = hashlib.md5(canonical.encode()).hexdigest()[:16]
    return f"live_matches:{digest}"


def _convert_raw_issue_to_match_dict(
    raw_issue: dict,
    raw_repo: dict,
    user_skills: dict,
    proxy_score: float,
) -> dict:
    """
    Convert a raw GitHub Search API issue object into the internal match dict
    shape used by the API response serialiser.
    """
    labels = [lbl["name"] for lbl in raw_issue.get("labels", [])]
    now_iso = datetime.now(timezone.utc).isoformat()
    matching_skills = _find_live_matching_skills(user_skills, raw_issue, raw_repo)
    return {
        "issue": {
            "id": None,
            "github_id": raw_issue.get("id"),
            "number": raw_issue.get("number"),
            "title": raw_issue.get("title", ""),
            "body": (raw_issue.get("body") or "")[:2000],
            "html_url": raw_issue.get("html_url", ""),
            "state": "open",
            "labels": labels,
            "is_good_first_issue": "good first issue" in [label.lower() for label in labels],
            "is_help_wanted": "help wanted" in [label.lower() for label in labels],
            "required_skills": {},
            "complexity_score": 0.5,
            "comments": raw_issue.get("comments", 0),
            "created_at": raw_issue.get("created_at"),
        },
        "repository": {
            "id": None,
            "full_name": raw_repo.get("full_name", ""),
            "name": raw_repo.get("name", ""),
            "description": raw_repo.get("description"),
            "owner_login": (raw_repo.get("full_name") or "").split("/")[0] if raw_repo.get("full_name") else "",
            "html_url": raw_repo.get("html_url", ""),
            "stars": raw_repo.get("stargazers_count") or raw_repo.get("stars", 0),
            "primary_language": raw_repo.get("language", ""),
            "topics": raw_repo.get("topics", []),
        },
        "match_score": proxy_score,
        "matching_skills": matching_skills,
        "why_matched": build_live_issue_explanation(
            user_skills, raw_issue, raw_repo, proxy_score
        ),
        "_is_live": True,
        "_raw_github_id": raw_issue.get("id"),
        "is_live_result": True,
        "live_fetched_at": now_iso,
    }


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


async def _persist_high_score_issues(
    live_matches: list[dict],
) -> None:
    """
    Background fire-and-forget task.
    For each live match above PERSIST_SCORE_THRESHOLD, upsert the issue into
    the PostgreSQL issues table and generate a skill_vector embedding.

    Creates its own database session so it can safely run as a background
    task without holding a reference to the request-scoped session.
    """
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
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

                result = await db.execute(
                    select(Issue).where(Issue.github_id == github_id)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    existing.updated_at = match.get("updated_at")
                    existing.comments = match.get("comments", existing.comments)
                    continue

                repo_result = await db.execute(
                    select(Repository).where(
                        Repository.full_name == match["repository"]["full_name"]
                    )
                )
                repo_obj = repo_result.scalar_one_or_none()
                if not repo_obj:
                    repo_obj = Repository(
                        github_id=_stable_hash(match["repository"]["full_name"], 2**31),
                        full_name=match["repository"]["full_name"],
                        name=match["repository"]["name"],
                        owner_login=match["repository"]["owner_login"],
                        html_url=match["repository"]["html_url"],
                        stars=match["repository"]["stars"],
                        primary_language=match["repository"]["primary_language"],
                        topics=match["repository"]["topics"],
                        is_archived=False,
                    )
                    db.add(repo_obj)
                    await db.flush()

                vector = await issue_text_to_vector(
                    title=match["issue"]["title"],
                    body=match["issue"].get("body") or "",
                    labels=match["issue"].get("labels") or [],
                )

                new_issue = Issue(
                    github_id=github_id,
                    number=match["issue"]["number"],
                    title=match["issue"]["title"],
                    body=(match["issue"].get("body") or "")[:10000],
                    html_url=match["issue"]["html_url"],
                    state="open",
                    labels=match["issue"]["labels"],
                    is_good_first_issue=match["issue"]["is_good_first_issue"],
                    is_help_wanted=match["issue"]["is_help_wanted"],
                    comments=match["issue"]["comments"],
                    skill_vector=vector,
                    complexity_score=0.5,
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
    extracted from the old get_matched_issues() body.
    """
    if user.skill_vector is None:
        return []

    pool_size = min(max(offset + limit, limit * 5), 500)

    stmt = (
        select(Issue, Repository)
        .join(Repository, Issue.repository_id == Repository.id)
        .where(
            Issue.state == "open",
            Issue.skill_vector.isnot(None),
            Repository.is_archived.is_(False),
        )
    )

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

    stmt = stmt.limit(pool_size)

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return []

    user_vec = user.skill_vector
    user_skills = user.skill_json or {}

    matches = []
    for issue, repo in rows:
        try:
            skill_sim = cosine_similarity(user_vec, issue.skill_vector)

            activity  = compute_repo_activity_score(repo)
            freshness = compute_freshness_score(issue)
            popularity = compute_popularity_score(issue, repo)
            interest  = compute_interest_match(
                user_skills,
                issue.required_skills or {},
            )

            final_score = (
                skill_sim  * SCORE_WEIGHTS["skill_match"]    +
                popularity * SCORE_WEIGHTS["popularity"]     +
                interest   * SCORE_WEIGHTS["interest_match"] +
                activity   * SCORE_WEIGHTS["repo_activity"]  +
                freshness  * SCORE_WEIGHTS["freshness"]
            )

            matched_skills = find_matching_skills(
                user_skills,
                issue.required_skills or {},
            )

            explanation = safe_explain_score(
                skill_sim, activity, freshness, interest, popularity,
                matched_skills,
                fallback_score=final_score,
                issue_id=issue.github_id,
            )

            matches.append({
                "issue": issue,
                "repository": repo,
                "match_score": round(final_score, 4),
                "matching_skills": matched_skills,
                "why_matched": explanation,
                "_is_live": False,
                "_raw_github_id": issue.github_id,
                "is_live_result": False,
                "live_fetched_at": None,
            })
        except Exception as exc:
            logger.warning(
                "Skipping issue github_id=%s due to scoring error: %s",
                issue.github_id, exc,
            )

    return matches


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
            continue
        match_dict = _convert_raw_issue_to_match_dict(
            raw_issue, raw_repo, skill_json, proxy_score
        )
        matches.append(match_dict)

    return matches


async def get_matched_issues(
    db: AsyncSession,
    user: User,
    limit: int = 20,
    offset: int = 0,
    filters: dict | None = None,
    github_service_instance=None,
    cache=None,
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
            cached = await cache_get(cache_key)
            if cached:
                logger.debug("Live match cache HIT key=%s", cache_key)
                all_matches = cached
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

    db_results_or_err, live_results_or_err = await asyncio.gather(
        db_task, live_task, return_exceptions=True,
    )

    if isinstance(db_results_or_err, Exception):
        logger.error("DB matching task failed: %s", db_results_or_err)
        db_results = []
    else:
        db_results = db_results_or_err

    if isinstance(live_results_or_err, Exception):
        logger.error("Live GitHub fetch task failed: %s", live_results_or_err)
        live_results = []
    else:
        live_results = live_results_or_err

    # ── Deduplicate: DB results win over live if same github_id ─────────────
    db_github_ids: set[int] = {
        r.get("_raw_github_id") for r in db_results if r.get("_raw_github_id")
    }
    unique_live = [
        r for r in live_results if r.get("_raw_github_id") not in db_github_ids
    ]

    all_matches = db_results + unique_live

    # ── Re-rank the unified list ─────────────────────────────────────────────
    if user.skill_vector is not None:
        from app.services.search_service import re_rank_results
        all_matches = re_rank_results(all_matches, user)
    else:
        all_matches.sort(key=lambda m: m.get("match_score", 0), reverse=True)

    # ── Fire-and-forget persistence for high-score live issues ───────────────
    if unique_live:
        asyncio.create_task(
            _persist_high_score_issues(unique_live)
        )

    # ── Cache the full ranked list ───────────────────────────────────────────
    if cache and all_matches:
        try:
            serialisable = []
            for m in all_matches:
                entry = dict(m)
                if isinstance(entry.get("issue"), Issue):
                    entry["issue"] = _issue_orm_to_dict(entry["issue"])
                if isinstance(entry.get("repository"), Repository):
                    entry["repository"] = _repo_orm_to_dict(entry["repository"])
                serialisable.append(entry)
            await cache_set(
                cache_key,
                serialisable,
                ttl=LIVE_MATCH_CACHE_TTL,
            )
        except Exception as exc:
            logger.warning("Redis cache write failed: %s", exc)

    # ── Paginate and return ──────────────────────────────────────────────────
    return all_matches[offset: offset + limit]


def _issue_orm_to_dict(issue: Issue) -> dict:
    return {
        "id": issue.id,
        "github_id": issue.github_id,
        "number": issue.number,
        "title": issue.title,
        "body": issue.body,
        "html_url": issue.html_url,
        "state": issue.state,
        "labels": issue.labels,
        "is_good_first_issue": issue.is_good_first_issue,
        "is_help_wanted": issue.is_help_wanted,
        "required_skills": issue.required_skills,
        "complexity_score": issue.complexity_score,
        "comments": issue.comments,
        "created_at": issue.created_at.isoformat() if issue.created_at else None,
    }


def _repo_orm_to_dict(repo: Repository) -> dict:
    return {
        "id": repo.id,
        "full_name": repo.full_name,
        "name": repo.name,
        "description": repo.description,
        "owner_login": repo.owner_login,
        "html_url": repo.html_url,
        "stars": repo.stars,
        "primary_language": repo.primary_language,
        "topics": repo.topics,
    }


def _keyword_score(user_skills: Dict[str, Any], issue: Issue) -> float:
    user_langs = set(user_skills.get("languages", {}).keys())
    user_topics = set(user_skills.get("topics", []))
    all_user_skills = user_langs | user_topics

    issue_text = f"{issue.title or ''} {issue.body or ''}".lower()
    issue_labels = [lb.lower() for lb in (issue.labels or [])]

    matches = sum(
        1 for skill in all_user_skills
        if skill in issue_text or any(skill in lbl for lbl in issue_labels)
    )

    total = max(len(all_user_skills), 1)
    return min(matches / total, 1.0)


async def search_issues_keyword(
    db: AsyncSession,
    query: str,
    language_filter: Optional[str] = None,
    difficulty: Optional[str] = None,
    label_filter: Optional[str] = None,
    limit: int = 30,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    conditions = [Issue.state == "open"]

    if query:
        like_pattern = f"%{query}%"
        conditions.append(
            or_(
                Issue.title.ilike(like_pattern),
                Issue.body.ilike(like_pattern),
            )
        )

    if language_filter:
        conditions.append(Repository.primary_language.ilike(language_filter))

    if difficulty == "beginner":
        conditions.append(Issue.complexity_score < 0.35)
    elif difficulty == "intermediate":
        conditions.append(Issue.complexity_score.between(0.35, 0.65))
    elif difficulty == "advanced":
        conditions.append(Issue.complexity_score > 0.65)

    if label_filter == "good_first":
        conditions.append(Issue.is_good_first_issue.is_(True))
    elif label_filter == "help_wanted":
        conditions.append(Issue.is_help_wanted.is_(True))

    query_stmt = (
        select(Issue, Repository)
        .join(Repository, Issue.repository_id == Repository.id)
        .where(and_(*conditions))
        .order_by(Issue.updated_at.desc().nullslast())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query_stmt)
    rows = result.fetchall()

    scored = []
    for issue, repo in rows:
        scored.append({
            "issue": issue,
            "repository": repo,
            "match_score": 0.5,
            "matching_skills": [],
            "why_matched": f"Matched your search: {query}" if query else "All open issues",
        })

    return scored
