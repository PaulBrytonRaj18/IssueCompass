import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Issue, SavedSearch
from app.routes.auth import get_current_user
from app.schemas.schemas import (
    SavedSearchCreate,
    SavedSearchPublic,
    SavedSearchUpdate,
)
from app.services import search_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/searches", tags=["searches"])


@router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=2),
    limit: int = Query(8, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Get search suggestions (languages, categories) for autocomplete."""
    suggestions = await search_service.get_suggestions(db, q, limit=limit)
    from app.schemas.schemas import SuggestionItem, SuggestionResult
    return SuggestionResult(suggestions=[SuggestionItem(**s) for s in suggestions])


@router.post("/save", response_model=SavedSearchPublic)
async def create_saved_search(
    body: SavedSearchCreate,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Save a search query for later."""
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token, db)

    saved = SavedSearch(
        user_id=user.id,
        name=body.name,
        query=body.query,
        filters=body.filters.model_dump() if body.filters else None,
        notify=body.notify,
    )
    db.add(saved)
    await db.commit()
    await db.refresh(saved)
    return saved


@router.get("/", response_model=List[SavedSearchPublic])
async def list_saved_searches(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """List user's saved searches."""
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token, db)

    result = await db.execute(
        select(SavedSearch)
        .where(SavedSearch.user_id == user.id)
        .order_by(SavedSearch.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{search_id}", response_model=SavedSearchPublic)
async def get_saved_search(
    search_id: int,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific saved search."""
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token, db)

    result = await db.execute(
        select(SavedSearch).where(
            SavedSearch.id == search_id,
            SavedSearch.user_id == user.id,
        )
    )
    saved = result.scalar_one_or_none()
    if not saved:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return saved


@router.put("/{search_id}", response_model=SavedSearchPublic)
async def update_saved_search(
    search_id: int,
    body: SavedSearchUpdate,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Update a saved search."""
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token, db)

    result = await db.execute(
        select(SavedSearch).where(
            SavedSearch.id == search_id,
            SavedSearch.user_id == user.id,
        )
    )
    saved = result.scalar_one_or_none()
    if not saved:
        raise HTTPException(status_code=404, detail="Saved search not found")

    if body.name is not None:
        saved.name = body.name
    if body.notify is not None:
        saved.notify = body.notify

    await db.commit()
    await db.refresh(saved)
    return saved


@router.delete("/{search_id}")
async def delete_saved_search(
    search_id: int,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Delete a saved search."""
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token, db)

    result = await db.execute(
        select(SavedSearch).where(
            SavedSearch.id == search_id,
            SavedSearch.user_id == user.id,
        )
    )
    saved = result.scalar_one_or_none()
    if not saved:
        raise HTTPException(status_code=404, detail="Saved search not found")

    await db.delete(saved)
    await db.commit()
    return {"message": "Saved search deleted"}


@router.post("/{search_id}/check")
async def check_saved_search(
    search_id: int,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Check a saved search for new issues since last check."""
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token, db)

    result = await db.execute(
        select(SavedSearch).where(
            SavedSearch.id == search_id,
            SavedSearch.user_id == user.id,
        )
    )
    saved = result.scalar_one_or_none()
    if not saved:
        raise HTTPException(status_code=404, detail="Saved search not found")

    results = await search_service.smart_search(
        db=db,
        query=saved.query,
        user=user,
        limit=10,
        offset=0,
    )

    new_count = 0
    if saved.last_checked_at:
        new_count = sum(
            1 for r in results
            if r["issue"].created_at and r["issue"].created_at > saved.last_checked_at
        )

    saved.last_checked_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    await db.commit()

    return {
        "total_results": len(results),
        "new_since_last_check": new_count,
    }
