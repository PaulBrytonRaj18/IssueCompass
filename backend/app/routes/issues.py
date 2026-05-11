import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.models.models import Issue, Repository, SavedIssue, User
from app.routes.auth import get_current_user
from app.schemas.schemas import IssueMatchResponse, IssuePublic, MatchedIssue, RepositoryPublic
from app.services import github_service, matching_service, skill_service

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

    return IssueMatchResponse(
        matches=matches,
        total=len(matches),
        user_skills=user_skills,
    )


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
    logger.info("Indexing complete: %d items processed", total)


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
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).replace(tzinfo=None)
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
