"""Image storage: S3 (production) with a local disk fallback for development."""
from __future__ import annotations

import uuid
from pathlib import Path

from starlette.concurrency import run_in_threadpool

from .config import get_settings

ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
}


def detect_image_type(content: bytes) -> str | None:
    """Identify the image type from magic bytes rather than trusting headers."""
    if content[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if content[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    if content[4:12] == b"ftypavif":
        return "image/avif"
    return None


def _put_to_s3(name: str, content: bytes, content_type: str) -> None:
    import boto3

    settings = get_settings()
    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url or None,
        aws_access_key_id=settings.s3_access_key or None,
        aws_secret_access_key=settings.s3_secret_key or None,
        region_name=settings.s3_region,
    )
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=f"listings/{name}",
        Body=content,
        ContentType=content_type,
        CacheControl="public, max-age=31536000",
    )


async def save_image(content: bytes) -> str:
    """Persist an image and return its public URL."""
    settings = get_settings()
    detected = detect_image_type(content)
    if detected not in ALLOWED_TYPES:
        raise ValueError("Formato de imagen no permitido.")
    name = f"{uuid.uuid4().hex}{ALLOWED_TYPES[detected]}"

    if settings.use_s3:
        await run_in_threadpool(_put_to_s3, name, content, detected)
        base = settings.s3_public_base_url or (
            f"https://{settings.s3_bucket}.s3.{settings.s3_region}.amazonaws.com"
        )
        return f"{base.rstrip('/')}/listings/{name}"

    media = Path(settings.media_dir)
    media.mkdir(parents=True, exist_ok=True)
    (media / name).write_bytes(content)
    return f"{settings.media_url_prefix.rstrip('/')}/{name}"


def ensure_media_dir() -> None:
    settings = get_settings()
    if not settings.use_s3:
        Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
