"""Authentication and profile endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import (
    COOKIE_NAME,
    clear_session_cookie,
    create_session,
    get_current_user,
    get_optional_user,
    set_session_cookie,
)
from ..models import Session, User
from ..ratelimit import enforce_auth_rate_limit
from ..schemas import LoginIn, ProfileIn, RegisterIn, UserOut
from ..security import hash_password, hash_token, verify_password, warm_password_check

router = APIRouter(prefix="/api", tags=["auth"])


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=UserOut)
async def register(
    payload: RegisterIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    await enforce_auth_rate_limit(_client_key(request))
    existing = await db.scalar(select(User.id).where(User.email == payload.email))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este correo ya tiene una cuenta.")
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = await create_session(db, user)
    set_session_cookie(response, token)
    return user


@router.post("/login", response_model=UserOut)
async def login(
    payload: LoginIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    await enforce_auth_rate_limit(_client_key(request))
    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is None:
        warm_password_check(payload.password)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos."
        )
    if not verify_password(user.password_hash, payload.password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos."
        )
    token = await create_session(db, user)
    set_session_cookie(response, token)
    return user


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        await db.execute(
            delete(Session).where(Session.token_hash == hash_token(token))
        )
        await db.commit()
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me")
async def me(user: User | None = Depends(get_optional_user)):
    return UserOut.model_validate(user) if user else None


@router.patch("/profile", response_model=UserOut)
async def update_profile(
    payload: ProfileIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.name = payload.name
    await db.commit()
    await db.refresh(user)
    return user
