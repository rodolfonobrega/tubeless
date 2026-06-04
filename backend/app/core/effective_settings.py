"""Effective settings: env defaults merged with user overrides from DB.

Services that need the latest settings call `load_effective_settings()`
at the start of a request/background-task with a fresh DB session.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.settings_repository import SettingsRepository

logger = logging.getLogger(__name__)

# In-memory cache, invalidated when settings are updated via the API.
# Single-process uvicorn — this is safe. Would need Redis/messaging
# with multiple workers.
_cache: dict[str, Any] | None = None


def invalidate_cache() -> None:
    """Drop the cache so the next read re-queries the DB."""
    global _cache
    _cache = None


async def load_effective_settings(db: AsyncSession) -> dict[str, Any]:
    """Return merged settings (env defaults + DB overrides).

    Cached in memory until invalidated — avoids querying settings
    on every request. The settings API calls invalidate_cache() on PUT.
    """
    global _cache
    if _cache is not None:
        return _cache

    repo = SettingsRepository(db)
    settings = await repo.get_all()
    _cache = settings
    logger.debug("Effective settings loaded from DB")
    return settings


async def get_effective_setting(db: AsyncSession, key: str) -> Any:
    """Return a single effective setting value."""
    settings = await load_effective_settings(db)
    return settings.get(key)
