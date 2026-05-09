from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Header, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db, AsyncSessionLocal
from app.models.models import Issue, Repository, SavedIssue, User
from app.schemas.schemas import IssueMatchResponse, MatchedIssue, IssuePublic, RepositoryPublic
from app.services import github_service, skill_service, matching_service
from app.routes.auth import get_current_user

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
    """Background task to fetch and index issues from GitHub."""
    async with AsyncSessionLocal() as db:
        for language in languages:
            for label in ["good first issue", "help wanted"]:
                result = await github_service.search_issues_global(
                    language=language, label=label, per_page=50
                )
                items = result.get("items", [])
                for item in items:
                    await _upsert_issue(db, item)
        await db.commit()


async def _upsert_issue(db: AsyncSession, item: dict):
    """Insert or update an issue from GitHub API response."""
    try:
        repo_data = item.get("repository") or {}
        repo_url = item.get("repository_url", "")
        repo_full_name = repo_url.replace("https://api.github.com/repos/", "")

        # Upsert repository
        repo_result = await db.execute(
            select(Repository).where(Repository.full_name == repo_full_name)
        )
        repo = repo_result.scalar_one_or_none()
        if not repo:
            repo = Repository(
                github_id=repo_data.get("id", _stable_id(repo_full_name)),
                full_name=repo_full_name,
                name=repo_full_name.split("/")[-1] if "/" in repo_full_name else repo_full_name,
                owner_login=repo_full_name.split("/")[0] if "/" in repo_full_name else "",
                html_url=f"https://github.com/{repo_full_name}",
                stars=repo_data.get("stargazers_count", 0),
                primary_language=repo_data.get("language"),
                topics=repo_data.get("topics", []),
                description=repo_data.get("description"),
            )
            db.add(repo)
            await db.flush()

        # Upsert issue
        issue_result = await db.execute(
            select(Issue).where(Issue.github_id == item["id"])
        )
        issue = issue_result.scalar_one_or_none()

        labels = [l["name"] for l in item.get("labels", [])]
        is_gfi = any("good first" in l.lower() for l in labels)
        is_hw = any("help wanted" in l.lower() for l in labels)

        title = item.get("title", "")
        body = item.get("body") or ""
        required_skills = skill_service.extract_required_skills(title, body, labels)
        skill_vector = skill_service.issue_text_to_vector(title, body, labels)
        complexity = required_skills.get("complexity", 0.5)

        if not issue:
            issue = Issue(
                github_id=item["id"],
                number=item["number"],
                title=title,
                body=body[:2000] if body else None,
                html_url=item["html_url"],
                state=item.get("state", "open"),
                labels=labels,
                is_good_first_issue=is_gfi,
                is_help_wanted=is_hw,
                required_skills=required_skills,
                skill_vector=skill_vector,
                complexity_score=complexity,
                comments=item.get("comments", 0),
                author_login=item.get("user", {}).get("login"),
                created_at=_parse_dt(item.get("created_at")),
                updated_at=_parse_dt(item.get("updated_at")),
                repository_id=repo.id,
            )
            db.add(issue)
        else:
            issue.state = item.get("state", "open")
            issue.comments = item.get("comments", 0)
            issue.updated_at = _parse_dt(item.get("updated_at"))
            issue.skill_vector = skill_vector
            issue.required_skills = required_skills

    except Exception as e:
        print(f"Error upserting issue {item.get('id')}: {e}")


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
