from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.models import User
from app.schemas.schemas import UserPublic, SkillFingerprint
from app.services import github_service, skill_service
from app.routes.auth import get_current_user

router = APIRouter(prefix="/github", tags=["github"])


@router.post("/analyze/{username}", response_model=UserPublic)
async def analyze_github_profile(
    username: str,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch GitHub data for a user, build skill fingerprint, store as vector.
    This is the core skill-building endpoint.
    """
    token = authorization.replace("Bearer ", "")
    current_user = await get_current_user(token, db)

    # Only allow analyzing own profile (or any profile for now for demo)
    target_username = username.lower()

    # Fetch repos
    repos = await github_service.fetch_user_repos(target_username)
    if not repos and not current_user:
        raise HTTPException(status_code=404, detail="GitHub user not found or no repos")

    # Build fingerprint
    fingerprint = skill_service.build_skill_fingerprint(repos)

    # Convert to vector
    skill_vector = skill_service.skill_fingerprint_to_vector(fingerprint)

    # Update user
    current_user.skill_json = fingerprint
    current_user.skill_vector = skill_vector
    current_user.skill_last_updated = datetime.utcnow()

    await db.commit()
    await db.refresh(current_user)

    return UserPublic.model_validate(current_user)


@router.get("/user/{username}")
async def get_github_user(username: str):
    """Proxy GitHub user data (public endpoint)."""
    user_data = await github_service.fetch_user(username)
    if not user_data:
        raise HTTPException(status_code=404, detail="GitHub user not found")
    return user_data


@router.get("/fingerprint", response_model=SkillFingerprint)
async def get_skill_fingerprint(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's skill fingerprint."""
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token, db)

    if not user.skill_json:
        raise HTTPException(
            status_code=404,
            detail="Skill fingerprint not generated yet. Run /github/analyze first.",
        )

    return SkillFingerprint(**user.skill_json)
