from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError

from app.core.config import get_settings
from app.core.database import get_db
from app.models.models import User
from app.schemas.schemas import TokenResponse, UserPublic, GitHubUserData
from app.services import github_service

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


@router.post("/github/callback", response_model=TokenResponse)
async def github_callback(
    github_data: GitHubUserData,
    db: AsyncSession = Depends(get_db),
):
    """
    Called by the Next.js frontend after GitHub OAuth completes.
    Creates or updates the user, returns a JWT.
    """
    # Find or create user
    result = await db.execute(
        select(User).where(User.github_id == github_data.github_id)
    )
    user = result.scalar_one_or_none()

    if user:
        # Update existing user
        user.github_avatar_url = github_data.github_avatar_url
        user.github_name = github_data.github_name
        user.github_bio = github_data.github_bio
        user.public_repos = github_data.public_repos
        user.followers = github_data.followers
        user.last_login = datetime.utcnow()
    else:
        # Create new user
        user = User(
            github_id=github_data.github_id,
            github_username=github_data.github_username,
            github_avatar_url=github_data.github_avatar_url,
            github_name=github_data.github_name,
            github_bio=github_data.github_bio,
            email=github_data.email,
            public_repos=github_data.public_repos,
            followers=github_data.followers,
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    access_token = create_access_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserPublic.model_validate(user),
    )


@router.get("/me", response_model=UserPublic)
async def get_me(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Get current user profile."""
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token, db)
    return UserPublic.model_validate(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Refresh the access token. Returns a new JWT."""
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token, db)
    user.last_login = datetime.utcnow()
    await db.commit()
    new_token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=new_token,
        token_type="bearer",
        user=UserPublic.model_validate(user),
    )
