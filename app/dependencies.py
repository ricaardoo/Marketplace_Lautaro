"""Shared FastAPI dependencies and session management."""
from __future__ import annotations

import time

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .database import get_db
from .models import Session, User
from .security import generate_token, hash_token

COOKIE_NAME = "session"


async def create_session(db: AsyncSession, user: User) -> str:
    settings = get_settings()
    token = generate_token()
    expires = int(time.time()) + settings.session_ttl_days * 86400
    await db.execute(delete(Session).where(Session.expires <= int(time.time())))
    db.add(Session(token_hash=hash_token(token), user_id=user.id, expires=expires))
    await db.commit()
    return token


def set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.session_ttl_days * 86400,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


async def get_optional_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    result = await db.execute(
        select(User)
        .join(Session, User.id == Session.user_id)
        .where(
            Session.token_hash == hash_token(token),
            Session.expires > int(time.time()),
        )
    )
    return result.scalar_one_or_none()


async def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inicia sesión para continuar.",
        )
    return user
