"""
GitHub REST API client with Redis-backed caching.

Every external HTTP call to GitHub is automatically cached via Redis,
reducing API consumption and improving response latency.
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.cache import cache_get_with_stale
from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

HEADERS = {
    "Authorization": f"token {settings.GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# Shared HTTPX client for connection reuse
_shared_client: Optional[httpx.AsyncClient] = None
_gh_rate_remaining: int = 5000  # start optimistic

# Limit concurrent live-fetch queries per request to avoid rate-limit burst
_LIVE_FETCH_SEMAPHORE = asyncio.Semaphore(4)


def _get_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None:
        _shared_client = httpx.AsyncClient(
            timeout=15.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
    return _shared_client


async def close_client() -> None:
    global _shared_client
    if _shared_client is not None:
        await _shared_client.aclose()
        _shared_client = None


async def _gh_request(method: str, url: str, **kwargs) -> httpx.Response:
    """Make a GitHub API request with rate-limit awareness and connection reuse."""
    global _gh_rate_remaining
    if _gh_rate_remaining < 10:
        logger.warning("GitHub rate limit critically low (%d remaining). Throttling.", _gh_rate_remaining)
        await asyncio.sleep(1)

    client = _get_client()
    resp = await client.request(method, url, headers=HEADERS, **kwargs)

    remaining = resp.headers.get("X-RateLimit-Remaining")
    if remaining is not None:
        _gh_rate_remaining = int(remaining)
        if _gh_rate_remaining < 100:
            logger.warning("GitHub rate limit low: %d remaining", _gh_rate_remaining)

    return resp

# Cache key prefixes
_GITHUB_CACHE_PREFIX = "gh:"

# TTLs in seconds based on data freshness
TTL_USER = 3600           # GitHub profile rarely changes
TTL_USER_REPOS = 1800     # Repos change with pushes
TTL_REPO_LANGUAGES = 86400  # Language mix is very stable
TTL_REPO_ISSUES = 600     # Issues change frequently
TTL_SEARCH_GLOBAL = 600   # Search results are time-sensitive
TTL_SEARCH_TEXT = 600
TTL_TRENDING_REPOS = 1800 # Trending changes daily


def _cache_key(*parts: str) -> str:
    return f"{_GITHUB_CACHE_PREFIX}{':'.join(parts)}"


async def _cached_fetch(cache_key: str, ttl: int, fetcher) -> Any:
    """Fetch with stale-while-revalidate cache pattern and dedup."""
    return await cache_get_with_stale(cache_key, ttl, fetcher)


async def fetch_user(username: str) -> Optional[Dict[str, Any]]:
    """Fetch a GitHub user's public profile. Cached 1 hour."""
    key = _cache_key("user", username.lower())

    async def _fetch():
        resp = await _gh_request("GET", f"{settings.GITHUB_API_BASE}/users/{username}")
        if resp.status_code == 200:
            return resp.json()
        return None

    return await _cached_fetch(key, TTL_USER, _fetch)


async def fetch_user_repos(username: str, per_page: int = 100) -> List[Dict[str, Any]]:
    """Fetch all public repos for a user. Cached 30 minutes."""
    key = _cache_key("repos", username.lower())

    async def _fetch():
        repos = []
        page = 1
        while True:
            resp = await _gh_request(
                "GET",
                f"{settings.GITHUB_API_BASE}/users/{username}/repos",
                params={
                    "per_page": per_page,
                    "page": page,
                    "sort": "updated",
                    "type": "owner",
                },
            )
            if resp.status_code != 200:
                break
            data = resp.json()
            if not data:
                break
            repos.extend(data)
            if len(data) < per_page:
                break
            page += 1
        return repos

    return await _cached_fetch(key, TTL_USER_REPOS, _fetch)


async def fetch_repo_languages(full_name: str) -> Dict[str, int]:
    """Fetch language breakdown for a repo. Cached 24 hours."""
    key = _cache_key("lang", full_name.lower().replace("/", ":"))

    async def _fetch():
        resp = await _gh_request(
            "GET",
            f"{settings.GITHUB_API_BASE}/repos/{full_name}/languages",
        )
        if resp.status_code == 200:
            return resp.json()
        return {}

    return await _cached_fetch(key, TTL_REPO_LANGUAGES, _fetch)


async def fetch_issues_for_repo(
    full_name: str,
    labels: str = "good first issue,help wanted",
    state: str = "open",
    per_page: int = 30,
) -> List[Dict[str, Any]]:
    """Fetch issues from a specific repo. Cached 10 minutes."""
    key = _cache_key("issues", full_name.lower().replace("/", ":"), labels, state, str(per_page))

    async def _fetch():
        resp = await _gh_request(
            "GET",
            f"{settings.GITHUB_API_BASE}/repos/{full_name}/issues",
            params={
                "labels": labels,
                "state": state,
                "per_page": per_page,
                "sort": "updated",
            },
        )
        if resp.status_code == 200:
            return [i for i in resp.json() if "pull_request" not in i]
        return []

    return await _cached_fetch(key, TTL_REPO_ISSUES, _fetch)


async def search_issues_global(
    language: Optional[str] = None,
    label: str = "good first issue",
    per_page: int = 50,
    page: int = 1,
) -> Dict[str, Any]:
    """Search GitHub for good first issues globally. Cached 10 minutes."""
    key = _cache_key(
        "search-global",
        hashlib.md5(f"{language or ''}:{label}:{per_page}:{page}".encode()).hexdigest()[:12],
    )

    async def _fetch():
        query = f'label:"{label}" state:open'
        if language:
            query += f" language:{language}"

        resp = await _gh_request(
            "GET",
            f"{settings.GITHUB_API_BASE}/search/issues",
            params={
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": per_page,
                "page": page,
            },
        )
        if resp.status_code == 200:
            return resp.json()
        return {"items": [], "total_count": 0}

    return await _cached_fetch(key, TTL_SEARCH_GLOBAL, _fetch)


async def search_issues_free_text(
    query: str,
    language: Optional[str] = None,
    per_page: int = 30,
    page: int = 1,
) -> Dict[str, Any]:
    """Search GitHub issues by free text query. Cached 10 minutes."""
    key = _cache_key(
        "search-text",
        hashlib.md5(f"{query.lower()}:{language or ''}:{per_page}:{page}".encode()).hexdigest()[:12],
    )

    async def _fetch():
        q = f'{query} state:open'
        if language:
            q += f" language:{language}"

        resp = await _gh_request(
            "GET",
            f"{settings.GITHUB_API_BASE}/search/issues",
            params={
                "q": q,
                "sort": "updated",
                "order": "desc",
                "per_page": per_page,
                "page": page,
            },
        )
        if resp.status_code == 200:
            return resp.json()
        return {"items": [], "total_count": 0}

    return await _cached_fetch(key, TTL_SEARCH_TEXT, _fetch)


async def search_trending_repos(
    language: Optional[str] = None,
    per_page: int = 30,
) -> List[Dict[str, Any]]:
    """Search for recently active, popular repos. Cached 30 minutes."""
    key = _cache_key("trending", language or "all", str(per_page))

    async def _fetch():
        since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        query = f"stars:>100 pushed:>{since} fork:false"
        if language:
            query += f" language:{language}"

        resp = await _gh_request(
            "GET",
            f"{settings.GITHUB_API_BASE}/search/repositories",
            params={
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": per_page,
            },
        )
        if resp.status_code == 200:
            return resp.json().get("items", [])
        return []

    return await _cached_fetch(key, TTL_TRENDING_REPOS, _fetch)


async def fetch_live_issues_for_user(
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
    """
    if not skill_json:
        return []

    # ── Rate-limit budget check ───────────────────────────────────────────
    global _gh_rate_remaining
    if _gh_rate_remaining < 50:
        logger.warning(
            "GitHub rate limit low (%d remaining) — skipping live fetch",
            _gh_rate_remaining,
        )
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
                raw = await search_issues_free_text(
                    q,
                    per_page=per_language_limit,
                )
                results = raw.get("items", [])
                # Normalise: attach _repo from the nested repository field
                enriched = []
                for issue in results:
                    repo = issue.get("repository") or {}
                    issue["_repo"] = repo
                    enriched.append(issue)
                return enriched
            except Exception:
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
