"""Authenticated image uploads for listings."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from ..config import get_settings
from ..dependencies import get_current_user
from ..models import User
from ..storage import save_image

router = APIRouter(prefix="/api", tags=["uploads"])


@router.post("/uploads")
async def upload_image(
    file: UploadFile = File(...),
    _user: User = Depends(get_current_user),
):
    settings = get_settings()
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "La imagen supera el tamaño máximo permitido (5 MB).",
        )
    try:
        url = await save_image(content)
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error))
    return {"url": url}
