"""Public marketplace statistics."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..cache import get_cache
from ..config import get_settings
from ..database import get_db
from ..models import Listing

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)):
    cache = get_cache()
    cached = await cache.get("stats:summary")
    if cached is not None:
        return cached

    listings = await db.scalar(
        select(func.count()).select_from(Listing).where(Listing.status == "active")
    )
    sellers = await db.scalar(
        select(func.count(func.distinct(Listing.user_id))).where(
            Listing.status == "active"
        )
    )
    cities = await db.scalar(
        select(func.count(func.distinct(Listing.city))).where(
            Listing.status == "active"
        )
    )
    result = {
        "listings": int(listings or 0),
        "sellers": int(sellers or 0),
        "cities": int(cities or 0),
    }
    await cache.set("stats:summary", result, get_settings().cache_ttl_seconds)
    return result
