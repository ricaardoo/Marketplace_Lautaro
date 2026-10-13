"""Listing catalog endpoints: browse, search, detail and CRUD."""
from __future__ import annotations

import hashlib
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..cache import get_cache, invalidate_catalog_cache
from ..config import get_settings
from ..database import get_db
from ..dependencies import get_current_user, get_optional_user
from ..models import Favorite, Listing, User
from ..schemas import ListingIn, ListingUpdate

router = APIRouter(prefix="/api", tags=["listings"])

_ORDERS = {
    "recent": (Listing.created_at.desc(), Listing.id.desc()),
    "price_asc": (Listing.price.asc(), Listing.id.desc()),
    "price_desc": (Listing.price.desc(), Listing.id.desc()),
}


def _int_param(value: str | None, default: int, minimum: int, maximum: int) -> int:
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parámetro numérico inválido.")
    if parsed < minimum or parsed > maximum:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parámetro fuera de rango.")
    return parsed


def _build_filters(params, user: User | None):
    conditions = []
    search = (params.get("q") or "").strip()[:200]
    if search:
        like = f"%{search}%"
        conditions.append(
            or_(
                Listing.title.ilike(like),
                Listing.description.ilike(like),
                Listing.city.ilike(like),
            )
        )
    for field in ("category", "city", "condition"):
        value = (params.get(field) or "").strip()
        if value:
            conditions.append(getattr(Listing, field) == value)

    mine = params.get("mine") == "1"
    favorites = params.get("favorites") == "1"
    if mine or favorites:
        if user is None:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "Inicia sesión para ver esta sección."
            )
        if mine:
            conditions.append(Listing.user_id == user.id)
        else:
            conditions.append(
                Listing.id.in_(
                    select(Favorite.listing_id).where(Favorite.user_id == user.id)
                )
            )
    else:
        conditions.append(Listing.status == "active")

    min_price = params.get("min_price")
    max_price = params.get("max_price")
    if min_price:
        conditions.append(
            Listing.price >= _int_param(min_price, 0, 0, 1_000_000_000)
        )
    if max_price:
        conditions.append(
            Listing.price <= _int_param(max_price, 0, 0, 1_000_000_000)
        )
    if min_price and max_price and int(min_price) > int(max_price):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "El precio mínimo no puede superar el máximo.",
        )

    sort = params.get("sort") or "recent"
    if sort not in _ORDERS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Orden no válido.")
    return conditions, _ORDERS[sort]


def _serialize(row) -> dict:
    listing, seller, contact, favorite, favorite_count = row
    return {
        "id": listing.id,
        "user_id": listing.user_id,
        "title": listing.title,
        "description": listing.description,
        "price": listing.price,
        "category": listing.category,
        "city": listing.city,
        "image": listing.image,
        "condition": listing.condition,
        "status": listing.status,
        "created_at": listing.created_at,
        "seller": seller,
        "contact": contact,
        "favorite": bool(favorite),
        "favorite_count": int(favorite_count or 0),
    }


def _select_listings(uid: int):
    favorite = (
        select(Favorite.user_id)
        .where(Favorite.listing_id == Listing.id, Favorite.user_id == uid)
        .exists()
    )
    favorite_count = (
        select(func.count())
        .select_from(Favorite)
        .where(Favorite.listing_id == Listing.id)
        .scalar_subquery()
    )
    return (
        select(Listing, User.name, User.email, favorite, favorite_count)
        .join(User, User.id == Listing.user_id)
    )


@router.get("/listings/count")
async def count_listings(
    request: Request,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    conditions, _ = _build_filters(request.query_params, user)
    cache = get_cache()
    key = "count:" + hashlib.sha1(
        repr(sorted(request.query_params.items())).encode()
    ).hexdigest()
    cached = await cache.get(key)
    if cached is not None:
        return cached
    total = await db.scalar(
        select(func.count()).select_from(Listing).where(*conditions)
    )
    result = {"total": int(total or 0)}
    await cache.set(key, result, get_settings().cache_ttl_seconds)
    return result


@router.get("/listings")
async def list_listings(
    request: Request,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    conditions, order = _build_filters(request.query_params, user)
    limit = _int_param(
        request.query_params.get("limit"), settings.default_page_size, 1, settings.max_page_size
    )
    offset = _int_param(request.query_params.get("offset"), 0, 0, 1_000_000_000)
    uid = user.id if user else 0
    stmt = (
        _select_listings(uid)
        .where(*conditions)
        .order_by(*order)
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(stmt)).all()
    return [_serialize(row) for row in rows]


@router.get("/listings/{listing_id}")
async def get_listing(
    listing_id: int,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    uid = user.id if user else 0
    row = (
        await db.execute(_select_listings(uid).where(Listing.id == listing_id))
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado.")
    return _serialize(row)


@router.post("/listings", status_code=status.HTTP_201_CREATED)
async def create_listing(
    payload: ListingIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = int(time.time())
    listing = Listing(
        user_id=user.id,
        title=payload.title,
        description=payload.description,
        price=payload.price,
        category=payload.category,
        city=payload.city,
        image=payload.image,
        condition=payload.condition,
        status="active",
        created_at=now,
        updated_at=now,
    )
    db.add(listing)
    await db.commit()
    await db.refresh(listing)
    await invalidate_catalog_cache()
    return {"id": listing.id}


@router.patch("/listings/{listing_id}")
async def update_listing(
    listing_id: int,
    payload: ListingUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    listing = await db.scalar(
        select(Listing).where(
            Listing.id == listing_id, Listing.user_id == user.id
        )
    )
    if listing is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Publicación no encontrada o no te pertenece."
        )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(listing, field, value)
    listing.updated_at = int(time.time())
    await db.commit()
    await invalidate_catalog_cache()
    return {"id": listing.id}


@router.delete("/listings/{listing_id}")
async def delete_listing(
    listing_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        delete(Listing).where(
            Listing.id == listing_id, Listing.user_id == user.id
        )
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Publicación no encontrada o no te pertenece."
        )
    await invalidate_catalog_cache()
    return {"ok": True}
