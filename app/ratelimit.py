"""Distributed-friendly rate limiting backed by the shared cache."""
from fastapi import HTTPException, status

from .cache import get_cache
from .config import get_settings


async def enforce_auth_rate_limit(client_key: str) -> None:
    """Limit register/login attempts per client for a rolling window."""
    settings = get_settings()
    cache = get_cache()
    count = await cache.hit(
        f"ratelimit:auth:{client_key}", settings.auth_rate_window_seconds
    )
    if count > settings.auth_rate_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Espera unos minutos e inténtalo otra vez.",
        )


async def clear_auth_rate_limit(client_key: str) -> None:
    cache = get_cache()
    await cache.reset(f"ratelimit:auth:{client_key}")
