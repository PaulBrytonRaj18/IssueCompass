import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query
from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete_pattern, cache_get, cache_set
from app.core.database import AsyncSessionLocal, get_db
from app.models.models import Issue, Repository, SavedIssue, User
from app.routes.auth import get_current_user
from app.schemas.schemas import (
    IssueMatchResponse,
    IssuePublic,
    MatchedIssue,
    RepositoryPublic,
    SearchResult,
    SmartSearchResult,
    TrendingResult,
)
from app.services import github_service, matching_service, search_service, skill_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/issues", tags=["issues"])


@router.get("/matches", response_model=IssueMatchResponse)
async def get_matched_issues(
    authorization: str = Header(...),
    language: Optional[str] = Query(None),
    label: Optional[str] = Query(None),
    limit: int = Query(30, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get personalized issue matches for the current user."""
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token, db)

    cache_key = f"matches:{user.id}:{language or ''}:{label or ''}:{limit}:{offset}"
    cached = await cache_get(cache_key)
    if cached:
        return IssueMatchResponse(**cached)

    matches_raw = await matching_service.get_matched_issues(
        db=db,
        user=user,
        limit=limit,
        offset=offset,
        language_filter=language,
        label_filter=label,
    )

    matches = []
    for m in matches_raw:
        issue = m["issue"]
        repo = m["repository"]
        matches.append(
            MatchedIssue(
                issue=IssuePublic(
                    id=issue.id,
                    github_id=issue.github_id,
                    number=issue.number,
                    title=issue.title,
                    body=issue.body,
                    html_url=issue.html_url,
                    state=issue.state,
                    labels=issue.labels,
                    is_good_first_issue=issue.is_good_first_issue,
                    is_help_wanted=issue.is_help_wanted,
                    required_skills=issue.required_skills,
                    complexity_score=issue.complexity_score,
                    comments=issue.comments,
                    created_at=issue.created_at,
                    repository=RepositoryPublic(
                        id=repo.id,
                        full_name=repo.full_name,
                        name=repo.name,
                        description=repo.description,
                        owner_login=repo.owner_login,
                        html_url=repo.html_url,
                        stars=repo.stars,
                        primary_language=repo.primary_language,
                        topics=repo.topics,
                    ),
                ),
                match_score=m["match_score"],
                matching_skills=m["matching_skills"],
                why_matched=m["why_matched"],
            )
        )

    from app.schemas.schemas import SkillFingerprint
    user_skills = None
    if user.skill_json:
        try:
            user_skills = SkillFingerprint(**user.skill_json)
        except Exception:
            pass

    response = IssueMatchResponse(
        matches=matches,
        total=len(matches),
        user_skills=user_skills,
    )
    await cache_set(cache_key, response.model_dump(), ttl=300)
    return response


@router.post("/index")
async def index_issues(
    background_tasks: BackgroundTasks,
    languages: List[str] = Query(
        default=["python", "javascript", "typescript", "go", "rust"]
    ),
):
    """
    Trigger background indexing of good-first-issues.
    In production, this runs on a cron schedule.
    """
    background_tasks.add_task(_index_issues_background, languages)
    return {"message": "Issue indexing started in background", "languages": languages}


async def _index_issues_background(languages: List[str]):
    """Background task to fetch and index issues from GitHub.
    Runs all language/label combinations in parallel for speed.
    Each task uses batch upserts to minimize DB round-trips.
    """
    labels = ["good first issue", "help wanted"]
    tasks = [
        _index_one(language, label)
        for language in languages
        for label in labels
    ]
    results = await asyncio.gather(*tasks)
    total = sum(results)
    await cache_delete_pattern("trending:*")
    logger.info("Indexing complete: %d items processed, cache invalidated", total)


async def _index_one(language: str, label: str) -> int:
    """Fetch and index issues for one language/label combination."""
    async with AsyncSessionLocal() as db:
        try:
            result = await github_service.search_issues_global(
                language=language, label=label, per_page=50
            )
            items = result.get("items", [])
            if not items:
                return 0
            await _batch_upsert(db, items)
            await db.commit()
            return len(items)
        except Exception as e:
            await db.rollback()
            logger.error("Error indexing %s/%s: %s", language, label, e)
            return 0


async def _batch_upsert(db: AsyncSession, items: List[dict]):
    """Batch upsert repositories and issues for a set of search results."""
    # Parse all items into a flat list
    parsed = []
    for item in items:
        repo_url = item.get("repository_url", "")
        repo_full_name = repo_url.replace("https://api.github.com/repos/", "")
        if not repo_full_name or "/" not in repo_full_name:
            continue
        repo_data = item.get("repository") or {}
        parsed.append({
            "item": item,
            "repo_full_name": repo_full_name,
            "repo_data": repo_data,
        })

    if not parsed:
        return

    # ── Batch upsert repositories ──────────────────────────────
    all_full_names = list({p["repo_full_name"] for p in parsed})

    existing_repos = await db.execute(
        select(Repository).where(Repository.full_name.in_(all_full_names))
    )
    repo_map = {r.full_name: r for r in existing_repos.scalars().all()}

    new_repos = []
    for full_name in all_full_names:
        if full_name in repo_map:
            continue
        p = next(p2 for p2 in parsed if p2["repo_full_name"] == full_name)
        rd = p["repo_data"]
        new_repos.append({
            "github_id": rd.get("id", _stable_id(full_name)),
            "full_name": full_name,
            "name": full_name.split("/")[-1],
            "owner_login": full_name.split("/")[0],
            "html_url": f"https://github.com/{full_name}",
            "stars": rd.get("stargazers_count", 0),
            "primary_language": rd.get("language"),
            "topics": rd.get("topics", []),
            "description": rd.get("description"),
        })

    if new_repos:
        stmt = pg_insert(Repository).values(new_repos)
        stmt = stmt.on_conflict_do_nothing(index_elements=["full_name"])
        await db.execute(stmt)
        await db.flush()

        # Re-query to get IDs of newly inserted repos
        result = await db.execute(
            select(Repository).where(Repository.full_name.in_(all_full_names))
        )
        repo_map = {r.full_name: r for r in result.scalars().all()}

    # ── Batch upsert issues ────────────────────────────────────
    all_github_ids = list({p["item"]["id"] for p in parsed})

    existing_issues = await db.execute(
        select(Issue).where(Issue.github_id.in_(all_github_ids))
    )
    existing_ids = {r.github_id for r in existing_issues.scalars().all()}

    new_issues = []
    for p in parsed:
        item = p["item"]
        if item["id"] in existing_ids:
            continue
        repo = repo_map.get(p["repo_full_name"])
        if not repo:
            continue

        labels = [lb["name"] for lb in item.get("labels", [])]
        title = item.get("title", "")
        body = item.get("body") or ""
        required_skills = skill_service.extract_required_skills(title, body, labels)
        skill_vector = skill_service.issue_text_to_vector(title, body, labels)
        complexity = required_skills.get("complexity", 0.5)

        new_issues.append({
            "github_id": item["id"],
            "number": item["number"],
            "title": title,
            "body": body[:2000] if body else None,
            "html_url": item["html_url"],
            "state": item.get("state", "open"),
            "labels": labels,
            "is_good_first_issue": any("good first" in lb.lower() for lb in labels),
            "is_help_wanted": any("help wanted" in lb.lower() for lb in labels),
            "required_skills": required_skills,
            "skill_vector": skill_vector,
            "complexity_score": complexity,
            "comments": item.get("comments", 0),
            "author_login": item.get("user", {}).get("login"),
            "created_at": _parse_dt(item.get("created_at")),
            "updated_at": _parse_dt(item.get("updated_at")),
            "repository_id": repo.id,
        })

    if new_issues:
        stmt = pg_insert(Issue).values(new_issues)
        stmt = stmt.on_conflict_do_nothing(index_elements=["github_id"])
        await db.execute(stmt)


def _stable_id(value: str) -> int:
    """Deterministic stable hash for fallback IDs."""
    import hashlib
    return int(hashlib.md5(value.encode()).hexdigest()[:8], 16)


def _parse_dt(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


@router.post("/save/{issue_id}")
async def save_issue(
    issue_id: int,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Save an issue to user's list."""
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token, db)

    existing = await db.execute(
        select(SavedIssue).where(
            SavedIssue.user_id == user.id,
            SavedIssue.issue_id == issue_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"message": "Already saved"}

    saved = SavedIssue(user_id=user.id, issue_id=issue_id)
    db.add(saved)
    await db.commit()
    return {"message": "Issue saved"}


@router.get("/saved", response_model=List[IssuePublic])
async def get_saved_issues(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Get user's saved issues."""
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token, db)

    result = await db.execute(
        select(Issue, Repository)
        .join(Repository, Issue.repository_id == Repository.id)
        .join(SavedIssue, SavedIssue.issue_id == Issue.id)
        .where(SavedIssue.user_id == user.id)
    )
    rows = result.fetchall()

    issues = []
    for issue, repo in rows:
        issues.append(
            IssuePublic(
                id=issue.id,
                github_id=issue.github_id,
                number=issue.number,
                title=issue.title,
                body=issue.body,
                html_url=issue.html_url,
                state=issue.state,
                labels=issue.labels,
                is_good_first_issue=issue.is_good_first_issue,
                is_help_wanted=issue.is_help_wanted,
                required_skills=issue.required_skills,
                complexity_score=issue.complexity_score,
                comments=issue.comments,
                created_at=issue.created_at,
                repository=RepositoryPublic.model_validate(repo),
            )
        )
    return issues


@router.get("/search", response_model=SearchResult)
async def search_issues(
    q: str = Query(..., min_length=1, description="Free-text search query"),
    language: Optional[str] = Query(None, description="Filter by language"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty: beginner, intermediate, advanced"),
    label: Optional[str] = Query(None, description="Filter by label: good_first, help_wanted"),
    limit: int = Query(30, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Search indexed issues by keyword with filters. Falls back to GitHub API if local results are sparse."""
    cache_key = f"search:{q}:{language or ''}:{difficulty or ''}:{label or ''}:{limit}:{offset}"

    cached = await cache_get(cache_key)
    if cached:
        return SearchResult(**cached)

    matches_raw = await matching_service.search_issues_keyword(
        db=db,
        query=q,
        language_filter=language,
        difficulty=difficulty,
        label_filter=label,
        limit=limit,
        offset=offset,
    )

    if len(matches_raw) < 5:
        github_results = await github_service.search_issues_free_text(
            query=q, language=language, per_page=limit
        )
        github_items = github_results.get("items", [])
        existing_ids = {m["issue"].github_id for m in matches_raw}

        for item in github_items:
            if item["id"] in existing_ids:
                continue
            repo_data = item.get("repository") or {}
            matches_raw.append({
                "issue": Issue(
                    github_id=item["id"],
                    number=item["number"],
                    title=item.get("title", ""),
                    body=(item.get("body") or "")[:2000],
                    html_url=item["html_url"],
                    state="open",
                    labels=[lb["name"] for lb in item.get("labels", [])],
                    is_good_first_issue=any("good first" in (lb.get("name", "") or "").lower() for lb in item.get("labels", [])),
                    is_help_wanted=any("help wanted" in (lb.get("name", "") or "").lower() for lb in item.get("labels", [])),
                    comments=item.get("comments", 0),
                    created_at=_parse_dt(item.get("created_at")),
                    updated_at=_parse_dt(item.get("updated_at")),
                    complexity_score=0.5,
                ),
                "repository": Repository(
                    full_name=repo_data.get("full_name", ""),
                    name=(repo_data.get("full_name") or "").split("/")[-1],
                    owner_login=(repo_data.get("full_name") or "").split("/")[0] if repo_data.get("full_name") else "",
                    html_url=repo_data.get("html_url", ""),
                    stars=repo_data.get("stargazers_count", 0),
                    primary_language=repo_data.get("language"),
                    description=repo_data.get("description"),
                ),
                "match_score": 0.5,
                "matching_skills": [],
                "why_matched": f"GitHub result for: {q}",
            })

    matches = []
    for m in matches_raw:
        issue = m["issue"]
        repo = m["repository"]
        matches.append(
            MatchedIssue(
                issue=IssuePublic(
                    id=getattr(issue, "id", 0),
                    github_id=getattr(issue, "github_id", 0),
                    number=getattr(issue, "number", 0),
                    title=issue.title,
                    body=getattr(issue, "body", None),
                    html_url=issue.html_url,
                    state=getattr(issue, "state", "open"),
                    labels=getattr(issue, "labels", []),
                    is_good_first_issue=getattr(issue, "is_good_first_issue", False),
                    is_help_wanted=getattr(issue, "is_help_wanted", False),
                    required_skills=getattr(issue, "required_skills", None),
                    complexity_score=getattr(issue, "complexity_score", 0.5),
                    comments=getattr(issue, "comments", 0),
                    created_at=getattr(issue, "created_at", None),
                    repository=RepositoryPublic(
                        id=getattr(repo, "id", 0),
                        full_name=repo.full_name,
                        name=getattr(repo, "name", ""),
                        description=getattr(repo, "description", None),
                        owner_login=repo.owner_login,
                        html_url=repo.html_url,
                        stars=getattr(repo, "stars", 0),
                        primary_language=getattr(repo, "primary_language", None),
                        topics=getattr(repo, "topics", None),
                    ),
                ),
                match_score=m["match_score"],
                matching_skills=m["matching_skills"],
                why_matched=m["why_matched"],
            )
        )

    result = SearchResult(matches=matches, total=len(matches), query=q)
    await cache_set(cache_key, result.model_dump(), ttl=1800)
    return result


@router.get("/trending", response_model=TrendingResult)
async def get_trending_issues(
    language: Optional[str] = Query(None, description="Filter trending by language"),
    limit: int = Query(20, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Return trending issues from active repositories."""
    cache_key = f"trending:{language or 'all'}:{limit}"

    cached = await cache_get(cache_key)
    if cached:
        return TrendingResult(**cached)

    trending_repos = await github_service.search_trending_repos(
        language=language, per_page=min(limit, 30)
    )

    if not trending_repos:
        return TrendingResult(matches=[], total=0, language=language)

    matches_raw = []
    for repo_data in trending_repos[:10]:
        full_name = repo_data.get("full_name", "")
        if not full_name:
            continue

        result = await db.execute(
            select(Issue, Repository)
            .join(Repository, Issue.repository_id == Repository.id)
            .where(
                and_(
                    Repository.full_name == full_name,
                    Issue.state == "open",
                    Issue.is_good_first_issue.is_(True),
                )
            )
            .order_by(Issue.updated_at.desc().nullslast())
            .limit(5)
        )
        rows = result.fetchall()

        if rows:
            for issue, repo in rows:
                matches_raw.append({
                    "issue": issue,
                    "repository": repo,
                    "match_score": 0.0,
                    "matching_skills": [],
                    "why_matched": f"Trending repository — {repo_data.get('stargazers_count', 0)} stars, active project",
                })
        else:
            github_issues = await github_service.fetch_issues_for_repo(
                full_name=full_name, labels="good first issue", per_page=3
            )
            for item in github_issues:
                matches_raw.append({
                    "issue": Issue(
                        github_id=item["id"],
                        number=item["number"],
                        title=item.get("title", ""),
                        body=(item.get("body") or "")[:2000],
                        html_url=item["html_url"],
                        state="open",
                        labels=[lb["name"] for lb in item.get("labels", [])],
                        is_good_first_issue=True,
                        is_help_wanted=any("help wanted" in (lb.get("name", "") or "").lower() for lb in item.get("labels", [])),
                        comments=item.get("comments", 0),
                        created_at=_parse_dt(item.get("created_at")),
                        updated_at=_parse_dt(item.get("updated_at")),
                        complexity_score=0.5,
                    ),
                    "repository": Repository(
                        full_name=full_name,
                        name=full_name.split("/")[-1],
                        owner_login=full_name.split("/")[0],
                        html_url=repo_data.get("html_url", f"https://github.com/{full_name}"),
                        stars=repo_data.get("stargazers_count", 0),
                        primary_language=repo_data.get("language"),
                        description=repo_data.get("description"),
                    ),
                    "match_score": 0.0,
                    "matching_skills": [],
                    "why_matched": f"Trending repository — {repo_data.get('stargazers_count', 0)} stars, active project",
                })

    matches = []
    for m in matches_raw:
        issue = m["issue"]
        repo = m["repository"]
        matches.append(
            MatchedIssue(
                issue=IssuePublic(
                    id=getattr(issue, "id", 0),
                    github_id=getattr(issue, "github_id", 0),
                    number=getattr(issue, "number", 0),
                    title=issue.title,
                    body=getattr(issue, "body", None),
                    html_url=issue.html_url,
                    state=getattr(issue, "state", "open"),
                    labels=getattr(issue, "labels", []),
                    is_good_first_issue=getattr(issue, "is_good_first_issue", False),
                    is_help_wanted=getattr(issue, "is_help_wanted", False),
                    required_skills=getattr(issue, "required_skills", None),
                    complexity_score=getattr(issue, "complexity_score", 0.5),
                    comments=getattr(issue, "comments", 0),
                    created_at=getattr(issue, "created_at", None),
                    repository=RepositoryPublic(
                        id=getattr(repo, "id", 0),
                        full_name=repo.full_name,
                        name=getattr(repo, "name", ""),
                        description=getattr(repo, "description", None),
                        owner_login=repo.owner_login,
                        html_url=repo.html_url,
                        stars=getattr(repo, "stars", 0),
                        primary_language=getattr(repo, "primary_language", None),
                        topics=getattr(repo, "topics", None),
                    ),
                ),
                match_score=m["match_score"],
                matching_skills=m["matching_skills"],
                why_matched=m["why_matched"],
            )
        )

    result = TrendingResult(matches=matches[:limit], total=len(matches[:limit]), language=language)
    await cache_set(cache_key, result.model_dump(), ttl=3600)
    return result


@router.get("/smart-search", response_model=SmartSearchResult)
async def smart_search_issues(
    q: str = Query(..., min_length=1, description="Natural language search query"),
    language: Optional[str] = Query(None, description="Filter by language"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    label: Optional[str] = Query(None, description="Filter by label"),
    limit: int = Query(30, le=100),
    offset: int = Query(0, ge=0),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Smart search with natural language understanding + optional personalization."""
    user = None
    if authorization:
        try:
            token = authorization.replace("Bearer ", "")
            user = await get_current_user(token, db)
        except Exception:
            pass

    cache_key = f"smart:{q}:{language or ''}:{difficulty or ''}:{label or ''}:{limit}:{offset}:{'auth' if user else 'anon'}"
    cached = await cache_get(cache_key)
    if cached:
        return SmartSearchResult(**cached)

    matches_raw = await search_service.smart_search(
        db=db,
        query=q,
        user=user,
        language_filter=language,
        difficulty=difficulty,
        label_filter=label,
        limit=limit,
        offset=offset,
        use_semantic=True,
    )

    intent = search_service.parse_natural_query(q)
    matches = []
    for m in matches_raw:
        issue = m["issue"]
        repo = m["repository"]
        matches.append(
            MatchedIssue(
                issue=IssuePublic(
                    id=getattr(issue, "id", 0),
                    github_id=getattr(issue, "github_id", 0),
                    number=getattr(issue, "number", 0),
                    title=issue.title,
                    body=getattr(issue, "body", None),
                    html_url=issue.html_url,
                    state=getattr(issue, "state", "open"),
                    labels=getattr(issue, "labels", []),
                    is_good_first_issue=getattr(issue, "is_good_first_issue", False),
                    is_help_wanted=getattr(issue, "is_help_wanted", False),
                    required_skills=getattr(issue, "required_skills", None),
                    complexity_score=getattr(issue, "complexity_score", 0.5),
                    comments=getattr(issue, "comments", 0),
                    created_at=getattr(issue, "created_at", None),
                    repository=RepositoryPublic(
                        id=getattr(repo, "id", 0),
                        full_name=repo.full_name,
                        name=getattr(repo, "name", ""),
                        description=getattr(repo, "description", None),
                        owner_login=repo.owner_login,
                        html_url=repo.html_url,
                        stars=getattr(repo, "stars", 0),
                        primary_language=getattr(repo, "primary_language", None),
                        topics=getattr(repo, "topics", None),
                    ),
                ),
                match_score=m["match_score"],
                matching_skills=m["matching_skills"],
                why_matched=m["why_matched"],
            )
        )

    result = SmartSearchResult(
        matches=matches,
        total=len(matches),
        query=q,
        intent={
            "keywords": intent.keywords,
            "languages": intent.languages,
            "difficulty": intent.difficulty,
            "labels": intent.labels,
            "categories": intent.categories,
        },
        personalized=user is not None,
    )
    await cache_set(cache_key, result.model_dump(), ttl=600)
    return result


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Platform statistics."""
    user_count = await db.execute(select(func.count(User.id)))
    issue_count = await db.execute(select(func.count(Issue.id)))
    repo_count = await db.execute(select(func.count(Repository.id)))

    return {
        "total_users": user_count.scalar() or 0,
        "total_issues_indexed": issue_count.scalar() or 0,
        "total_repos_indexed": repo_count.scalar() or 0,
    }
