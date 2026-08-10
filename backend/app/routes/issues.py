import logging
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user
from app.core.ratelimit import limiter
from app.core.utils import parse_dt
from app.models.models import Issue, Repository, SavedIssue, User
from app.schemas.schemas import (
    IssueMatchResponse,
    IssuePublic,
    MatchedIssue,
    RepositoryPublic,
    SmartSearchResult,
    TrendingResult,
)
from app.services import github_service, matching_service, search_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/issues", tags=["issues"])


def _to_repo_public(repo) -> RepositoryPublic:
    if isinstance(repo, dict):
        return RepositoryPublic.model_validate(repo)
    return RepositoryPublic.model_validate(repo)


def _to_issue_public(issue, repo=None) -> IssuePublic:
    pub = IssuePublic.model_validate(issue)
    if repo is not None:
        pub.repository = _to_repo_public(repo)
    return pub


@router.get("/matches", response_model=IssueMatchResponse)
async def get_matched_issues(
    request: Request,
    current_user: User = Depends(get_current_user),
    language: Optional[str] = Query(None, description="Filter by language"),
    is_good_first_issue: Optional[bool] = Query(None, description="Filter by good first issue"),
    is_help_wanted: Optional[bool] = Query(None, description="Filter by help wanted"),
    difficulty: Optional[Literal["beginner", "intermediate", "advanced"]] = Query(
        None, description="Filter by difficulty: beginner, intermediate, advanced"
    ),
    limit: int = Query(30, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get personalized issue matches for the current user. Combines DB + live GitHub results."""
    filters = {
        "language": language,
        "is_good_first_issue": is_good_first_issue,
        "is_help_wanted": is_help_wanted,
        "difficulty": difficulty,
    }
    filters = {k: v for k, v in filters.items() if v is not None}

    matches_raw = await matching_service.get_matched_issues(
        db=db,
        user=current_user,
        limit=limit,
        offset=offset,
        filters=filters,
        github_service_instance=github_service,
        cache=True,
    )

    matches = []
    for m in matches_raw:
        issue_pub = _to_issue_public(m["issue"], m["repository"])

        match_item = MatchedIssue(
            issue=issue_pub,
            match_score=m["match_score"],
            matching_skills=m["matching_skills"],
            why_matched=m["why_matched"],
        )
        if m.get("is_live_result"):
            match_item.is_live_result = True
            match_item.live_fetched_at = m.get("live_fetched_at")
        matches.append(match_item)

    from app.schemas.schemas import SkillFingerprint

    user_skills = None
    if current_user.skill_json:
        try:
            user_skills = SkillFingerprint(**current_user.skill_json)
        except Exception:
            pass

    return IssueMatchResponse(
        matches=matches,
        total=len(matches),
        user_skills=user_skills,
    )


@router.post("/index")
@limiter.limit("3/minute")  # Strict: triggers background worker
async def index_issues(
    request: Request,
    background_tasks: BackgroundTasks,
    languages: List[str] = Query(default=["python", "javascript", "typescript", "go", "rust"]),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger background indexing of issues.
    Uses ARQ worker when available, falls back to BackgroundTasks.
    Rate-limited to 3/minute to prevent abuse.
    """
    from app.worker import full_index

    background_tasks.add_task(full_index, None, languages)
    return {
        "message": "Issue indexing started in background",
        "languages": languages,
    }


@router.post("/save/{issue_id}")
@limiter.limit("30/minute")
async def save_issue(
    request: Request,
    issue_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save an issue to user's list."""
    user = current_user

    issue_exists = await db.execute(select(Issue).where(Issue.id == issue_id))
    if not issue_exists.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Issue not found")

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
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's saved issues."""
    user = current_user

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


@router.get("/trending", response_model=TrendingResult)
async def get_trending_issues(
    request: Request,
    language: Optional[str] = Query(None, description="Filter trending by language"),
    limit: int = Query(20, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Return trending issues from active repositories. Cached 1 hour."""
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
    repo_names = [r.get("full_name") for r in trending_repos[:10] if r.get("full_name")]
    if repo_names:
        db_result = await db.execute(
            select(Issue, Repository)
            .join(Repository, Issue.repository_id == Repository.id)
            .where(
                and_(
                    Repository.full_name.in_(repo_names),
                    Issue.state == "open",
                    Issue.is_good_first_issue.is_(True),
                )
            )
            .order_by(Issue.updated_at.desc().nullslast())
            .limit(limit)
        )
        indexed_rows = db_result.fetchall()
        indexed_by_repo: Dict[str, List] = {}
        for issue, repo in indexed_rows:
            indexed_by_repo.setdefault(repo.full_name, []).append((issue, repo))

        for repo_data in trending_repos[:10]:
            full_name = repo_data.get("full_name", "")
            if not full_name:
                continue

            rows = indexed_by_repo.get(full_name, [])
            if rows:
                for issue, repo in rows:
                    matches_raw.append(
                        {
                            "issue": issue,
                            "repository": repo,
                            "match_score": 0.0,
                            "matching_skills": [],
                            "why_matched": f"Trending repository — {repo_data.get('stargazers_count', 0)} stars, active project",
                        }
                    )
            else:
                github_issues = await github_service.fetch_issues_for_repo(
                    full_name=full_name, labels="good first issue", per_page=3
                )
                for item in github_issues:
                    matches_raw.append(
                        {
                            "issue": Issue(
                                github_id=item["id"],
                                number=item["number"],
                                title=item.get("title", ""),
                                body=(item.get("body") or "")[:2000],
                                html_url=item["html_url"],
                                state="open",
                                labels=[lb["name"] for lb in item.get("labels", [])],
                                is_good_first_issue=True,
                                is_help_wanted=any(
                                    "help wanted" in (lb.get("name", "") or "").lower()
                                    for lb in item.get("labels", [])
                                ),
                                comments=item.get("comments", 0),
                                created_at=parse_dt(item.get("created_at")),
                                updated_at=parse_dt(item.get("updated_at")),
                                complexity_score=0.5,
                            ),
                            "repository": Repository(
                                full_name=full_name,
                                name=full_name.split("/")[-1],
                                owner_login=full_name.split("/")[0],
                                html_url=repo_data.get(
                                    "html_url", f"https://github.com/{full_name}"
                                ),
                                stars=repo_data.get("stargazers_count", 0),
                                primary_language=repo_data.get("language"),
                                description=repo_data.get("description"),
                            ),
                            "match_score": 0.0,
                            "matching_skills": [],
                            "why_matched": f"Trending repository — {repo_data.get('stargazers_count', 0)} stars, active project",
                        }
                    )

    matches = []
    for m in matches_raw:
        matches.append(
            MatchedIssue(
                issue=_to_issue_public(m["issue"], m["repository"]),
                match_score=m["match_score"],
                matching_skills=m["matching_skills"],
                why_matched=m["why_matched"],
            )
        )

    result = TrendingResult(matches=matches[:limit], total=len(matches[:limit]), language=language)
    await cache_set(cache_key, result.model_dump(), ttl=3600)
    return result


@router.get("/smart-search", response_model=SmartSearchResult)
@limiter.limit("20/minute")  # Expensive: uses AI
async def smart_search_issues(
    request: Request,
    q: str = Query(..., min_length=1, description="Natural language search query"),
    language: Optional[str] = Query(None, description="Filter by language"),
    difficulty: Optional[Literal["beginner", "intermediate", "advanced"]] = Query(
        None, description="Filter by difficulty"
    ),
    label: Optional[Literal["good_first", "help_wanted"]] = Query(
        None, description="Filter by label"
    ),
    limit: int = Query(30, le=100),
    offset: int = Query(0, ge=0),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Smart search with natural language understanding + optional personalization. Rate-limited to 20/min. Cached 10 min."""
    user = current_user

    cache_key = f"smart:{q}:{language or ''}:{difficulty or ''}:{label or ''}:{limit}:{offset}:{'auth' if user else 'anon'}"
    cached = await cache_get(cache_key)
    if cached:
        return SmartSearchResult(**cached)

    matches_raw, intent = await search_service.smart_search(
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
    matches = []
    for m in matches_raw:
        matches.append(
            MatchedIssue(
                issue=_to_issue_public(m["issue"], m["repository"]),
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
async def get_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Platform statistics. Cached 5 minutes."""
    cache_key = "platform:stats"

    cached = await cache_get(cache_key)
    if cached:
        return cached

    user_count = await db.execute(select(func.count(User.id)))
    issue_count = await db.execute(select(func.count(Issue.id)))
    repo_count = await db.execute(select(func.count(Repository.id)))

    result = {
        "total_users": user_count.scalar() or 0,
        "total_issues_indexed": issue_count.scalar() or 0,
        "total_repos_indexed": repo_count.scalar() or 0,
    }
    await cache_set(cache_key, result, ttl=300)
    return result
