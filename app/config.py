"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Marketplace Lautaro"
    environment: str = "development"
    debug: bool = False

    # Persistence ---------------------------------------------------------
    database_url: str = (
        "postgresql+asyncpg://marketplace:marketplace@localhost:5432/marketplace"
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20
    auto_create_tables: bool = True

    # Sessions / security -------------------------------------------------
    secret_key: str = "dev-secret-key-change-in-production"
    cookie_secure: bool = False
    session_ttl_days: int = 7

    # Rate limiting -------------------------------------------------------
    auth_rate_limit: int = 20
    auth_rate_window_seconds: int = 300

    # Catalog -------------------------------------------------------------
    default_page_size: int = 24
    max_page_size: int = 200
    max_upload_bytes: int = 5 * 1024 * 1024

    # Cache / queue -------------------------------------------------------
    redis_url: str = ""
    cache_ttl_seconds: int = 30

    # Object storage (S3 compatible). When empty, local disk is used.
    s3_endpoint_url: str = ""
    s3_bucket: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"
    s3_public_base_url: str = ""

    media_dir: str = ".data/media"
    media_url_prefix: str = "/media"

    cors_origins: str = ""
    # Extra host appended to the CSP img-src (e.g. an S3/MinIO dev endpoint).
    csp_img_extra: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def use_s3(self) -> bool:
        return bool(self.s3_bucket)


@lru_cache
def get_settings() -> Settings:
    return Settings()
