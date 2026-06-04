"""Project repository."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.orm.project import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """Repository for Project model."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: The async database session.
        """
        super().__init__(Project, session)

    async def get_with_relations(self, id: uuid.UUID) -> Project | None:
        """Get project with all related entities.

        Args:
            id: The project UUID.

        Returns:
            Project with videos, summaries, etc. loaded or None.
        """
        stmt = (
            select(Project)
            .where(Project.id == id)
            .options(
                selectinload(Project.videos)
                .selectinload(Project.transcript)
                .selectinload(Project.summary),
                selectinload(Project.consolidated_summary),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_name(self, name: str) -> Project | None:
        """Get project by name.

        Args:
            name: The project name.

        Returns:
            Project instance or None.
        """
        return await self.get_by_field("name", name)

    async def list_by_status(
        self, status: str, offset: int = 0, limit: int = 100
    ) -> Sequence[Project]:
        """List projects by status.

        Args:
            status: The status to filter by.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Sequence of Project instances.
        """
        return await self.list(offset=offset, limit=limit, status=status, order_by="created_at")

    async def update_status(self, id: uuid.UUID, status: str) -> Project | None:
        """Update project status.

        Args:
            id: The project UUID.
            status: New status value.

        Returns:
            Updated Project or None.
        """
        return await self.update(id, status=status)

    async def increment_video_count(self, id: uuid.UUID) -> Project | None:
        """Increment video count for a project.

        Args:
            id: The project UUID.

        Returns:
            Updated Project or None.
        """
        project = await self.get(id)
        if project is None:
            return None

        project.video_count += 1
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def set_consolidated_summary(
        self, id: uuid.UUID, summary_id: uuid.UUID
    ) -> Project | None:
        """Set the consolidated summary for a project.

        Args:
            id: The project UUID.
            summary_id: The summary UUID.

        Returns:
            Updated Project or None.
        """
        return await self.update(id, consolidated_summary_id=summary_id)
