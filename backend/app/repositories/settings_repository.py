"""Repository for user-configurable application settings."""

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.orm.app_settings import AppSettings

logger = logging.getLogger(__name__)

# Pydantic settings (env defaults) — used as reference for which keys exist
_env_settings = get_settings()


class SettingsRepository:
    """Repository for reading/writing user setting overrides in the DB.

    When a user-set value equals the .env default, the row is deleted
    so we don't store redundant data.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _env_default(key: str) -> Any:
        """Return the .env default value for a given key."""
        return getattr(_env_settings, key, None)

    async def get_all(self) -> dict[str, Any]:
        """Return merged settings: env defaults + user overrides from DB."""
        result = await self.session.execute(select(AppSettings))
        rows = {row.key: row for row in result.scalars().all()}

        merged: dict[str, Any] = {}
        for key in AppSettings.USER_CONFIGURABLE_KEYS:
            default = self._env_default(key)
            if key in rows and rows[key].value is not None:
                try:
                    merged[key] = json.loads(rows[key].value)
                except (json.JSONDecodeError, TypeError):
                    merged[key] = rows[key].value
            else:
                merged[key] = default
        return merged

    async def get(self, key: str) -> Any:
        """Return effective value for one key (DB override or env default)."""
        result = await self.session.execute(
            select(AppSettings).where(AppSettings.key == key)
        )
        row = result.scalar_one_or_none()
        if row and row.value is not None:
            try:
                return json.loads(row.value)
            except (json.JSONDecodeError, TypeError):
                return row.value
        return self._env_default(key)

    async def set(self, key: str, value: Any) -> None:
        """Upsert a single setting. Delete row if value equals env default."""
        if key not in AppSettings.USER_CONFIGURABLE_KEYS:
            raise ValueError(f"Setting '{key}' is not user-configurable")

        default = self._env_default(key)
        result = await self.session.execute(
            select(AppSettings).where(AppSettings.key == key)
        )
        row = result.scalar_one_or_none()

        if value == default:
            if row:
                await self.session.delete(row)
            return

        serialized = json.dumps(value) if not isinstance(value, str) else value
        if row:
            row.value = serialized
        else:
            self.session.add(AppSettings(key=key, value=serialized))

        await self.session.flush()

    async def set_many(self, data: dict[str, Any]) -> None:
        """Upsert multiple settings at once."""
        for key, value in data.items():
            await self.set(key, value)

    async def cleanup_obsolete_keys(self) -> int:
        """Delete DB rows whose keys are no longer in USER_CONFIGURABLE_KEYS.

        Returns the number of rows deleted.
        """
        from sqlalchemy import delete
        stmt = (
            delete(AppSettings)
            .where(AppSettings.key.not_in(AppSettings.USER_CONFIGURABLE_KEYS))
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
