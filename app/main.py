"""Marketplace Lautaro — FastAPI application factory."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import get_settings
from .database import Base, engine
from .routers import auth, favorites, listings, stats, uploads
from .storage import ensure_media_dir

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"


def _csp(settings) -> str:
    img_extra = f" {settings.csp_img_extra}" if settings.csp_img_extra else ""
    return (
        "default-src 'self'; "
        f"img-src 'self' https: data:{img_extra}; "
        "style-src 'self'; script-src 'self'; connect-src 'self'; "
        "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    ensure_media_dir()
    if settings.auto_create_tables:
        from . import models  # noqa: F401  (register metadata)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    csp = _csp(settings)
    app = FastAPI(
        title=settings.app_name,
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.debug else None,
        redoc_url=None,
    )

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
            origin = request.headers.get("origin")
            if origin and urlsplit(origin).netloc != request.headers.get("host"):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"error": "Origen no permitido."},
                )
            if request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"error": "Origen no permitido."},
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = csp
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, exc: StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        message = "Revisa los datos enviados."
        errors = exc.errors()
        if errors:
            raw = str(errors[0].get("msg", ""))
            if raw.startswith("Value error, "):
                raw = raw[len("Value error, ") :]
            if raw:
                message = raw
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"error": message}
        )

    @app.exception_handler(Exception)
    async def unhandled_error(_request: Request, _exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "No se pudo completar la solicitud."},
        )

    app.include_router(auth.router)
    app.include_router(listings.router)
    app.include_router(favorites.router)
    app.include_router(stats.router)
    app.include_router(uploads.router)

    if not settings.use_s3:
        ensure_media_dir()
        app.mount(
            settings.media_url_prefix,
            StaticFiles(directory=settings.media_dir, check_dir=False),
            name="media",
        )
    app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="static")
    return app


app = create_app()
