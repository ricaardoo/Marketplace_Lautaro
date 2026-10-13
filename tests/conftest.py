"""Test configuration.

Locally this runs against a throwaway SQLite database and the in-memory cache.
In CI the DATABASE_URL/REDIS_URL are provided and respected.
"""
import os
import tempfile

import httpx
import pytest_asyncio

TMP = tempfile.mkdtemp(prefix="marketplace_tests_")

os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{TMP}/test.db")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("MEDIA_DIR", f"{TMP}/media")
os.environ.setdefault("AUTO_CREATE_TABLES", "false")
os.environ.setdefault("AUTH_RATE_LIMIT", "50")

from app import models  # noqa: E402,F401
from app.cache import get_cache  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest_asyncio.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    cache = get_cache()
    await cache.clear()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
