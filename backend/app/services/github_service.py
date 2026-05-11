from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings

settings = get_settings()

HEADERS = {
    "Authorization": f"token {settings.GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


async def fetch_user(username: str) -> Optional[Dict[str, Any]]:
    """Fetch a GitHub user's public profile."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.GITHUB_API_BASE}/users/{username}",
            headers=HEADERS,
            timeout=10.0,
        )
        if resp.status_code == 200:
            return resp.json()
        return None


async def fetch_user_repos(username: str, per_page: int = 100) -> List[Dict[str, Any]]:
    """Fetch all public repos for a user."""
    repos = []
    page = 1
    async with httpx.AsyncClient() as client:
        while True:
            resp = await client.get(
                f"{settings.GITHUB_API_BASE}/users/{username}/repos",
                headers=HEADERS,
                params={
                    "per_page": per_page,
                    "page": page,
                    "sort": "updated",
                    "type": "owner",
                },
                timeout=15.0,
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


async def fetch_repo_languages(full_name: str) -> Dict[str, int]:
    """Fetch language breakdown for a repo."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.GITHUB_API_BASE}/repos/{full_name}/languages",
            headers=HEADERS,
            timeout=10.0,
        )
        if resp.status_code == 200:
            return resp.json()
        return {}


async def fetch_issues_for_repo(
    full_name: str,
    labels: str = "good first issue,help wanted",
    state: str = "open",
    per_page: int = 30,
) -> List[Dict[str, Any]]:
    """Fetch issues from a specific repo."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.GITHUB_API_BASE}/repos/{full_name}/issues",
            headers=HEADERS,
            params={
                "labels": labels,
                "state": state,
                "per_page": per_page,
                "sort": "updated",
            },
            timeout=10.0,
        )
        if resp.status_code == 200:
            # Filter out pull requests (GitHub issues API includes PRs)
            return [i for i in resp.json() if "pull_request" not in i]
        return []


async def search_issues_global(
    language: Optional[str] = None,
    label: str = "good first issue",
    per_page: int = 50,
    page: int = 1,
) -> Dict[str, Any]:
    """Search GitHub for good first issues globally."""
    query = f'label:"{label}" state:open'
    if language:
        query += f" language:{language}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.GITHUB_API_BASE}/search/issues",
            headers=HEADERS,
            params={
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": per_page,
                "page": page,
            },
            timeout=15.0,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"items": [], "total_count": 0}


async def search_trending_repos(
    language: Optional[str] = None,
    per_page: int = 30,
) -> List[Dict[str, Any]]:
    """Search for recently active, popular repos."""
    from datetime import datetime, timedelta
    since = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")

    query = f"stars:>100 pushed:>{since} fork:false"
    if language:
        query += f" language:{language}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.GITHUB_API_BASE}/search/repositories",
            headers=HEADERS,
            params={
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": per_page,
            },
            timeout=15.0,
        )
        if resp.status_code == 200:
            return resp.json().get("items", [])
        return []
