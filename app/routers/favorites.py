"""Favorite listings endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..cache import invalidate_catalog_cache
from ..database import get_db
from ..dependencies import get_current_user
from ..models import Favorite, Listing, User

router = APIRouter(prefix="/api", tags=["favorites"])


@router.post("/favorites/{listing_id}")
async def add_favorite(
    listing_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    exists = await db.scalar(select(Listing.id).where(Listing.id == listing_id))
    if exists is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "El producto ya no está disponible."
        )
    current = await db.scalar(
        select(Favorite.user_id).where(
            Favorite.user_id == user.id, Favorite.listing_id == listing_id
        )
    )
    if current is None:
        db.add(Favorite(user_id=user.id, listing_id=listing_id))
        await db.commit()
        await invalidate_catalog_cache()
    return {"ok": True}


@router.delete("/favorites/{listing_id}")
async def remove_favorite(
    listing_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        delete(Favorite).where(
            Favorite.user_id == user.id, Favorite.listing_id == listing_id
        )
    )
    await db.commit()
    await invalidate_catalog_cache()
    return {"ok": True}
