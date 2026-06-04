"""Settings API endpoints — user-configurable application settings."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.effective_settings import invalidate_cache, load_effective_settings
from app.models.orm.app_settings import AppSettings
from app.repositories.settings_repository import SettingsRepository

logger = logging.getLogger(__name__)
router = APIRouter()


class SettingsResponse(BaseModel):
    """Current settings + env defaults for reference."""

    settings: dict[str, Any]
    defaults: dict[str, Any]


class SettingsUpdateRequest(BaseModel):
    """Request body for updating settings."""

    settings: dict[str, Any]


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    session: AsyncSession = Depends(get_session),
) -> SettingsResponse:
    """Return current effective settings and env defaults."""
    repo = SettingsRepository(session)
    effective = await load_effective_settings(session)

    from app.core.config import get_settings
    env = get_settings()
    defaults = {
        key: getattr(env, key, None)
        for key in AppSettings.USER_CONFIGURABLE_KEYS
    }

    return SettingsResponse(settings=effective, defaults=defaults)


@router.post("/settings/cleanup")
async def cleanup_settings(session: AsyncSession = Depends(get_session)) -> dict[str, int]:
    """Remove obsolete settings keys from DB that are no longer configurable."""
    repo = SettingsRepository(session)
    deleted = await repo.cleanup_obsolete_keys()
    await session.commit()
    invalidate_cache()
    return {"deleted_rows": deleted}


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    request: SettingsUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> SettingsResponse:
    """Update user settings. Only whitelisted keys are accepted."""
    invalid_keys = set(request.settings.keys()) - AppSettings.USER_CONFIGURABLE_KEYS
    if invalid_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown settings: {', '.join(sorted(invalid_keys))}",
        )

    repo = SettingsRepository(session)
    await repo.set_many(request.settings)
    await session.commit()
    invalidate_cache()

    effective = await load_effective_settings(session)

    from app.core.config import get_settings
    env = get_settings()
    defaults = {
        key: getattr(env, key, None)
        for key in AppSettings.USER_CONFIGURABLE_KEYS
    }

    return SettingsResponse(settings=effective, defaults=defaults)
