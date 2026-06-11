"""Video repository."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.orm.video import Video
from app.repositories.base import BaseRepository


class VideoRepository(BaseRepository[Video]):
    """Repository for Video model."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: The async database session.
        """
        super().__init__(Video, session)

    async def get_with_relations(self, id: uuid.UUID) -> Video | None:
        """Get video with all related entities.

        Args:
            id: The video UUID.

        Returns:
            Video with transcript, summary, etc. loaded or None.
        """
        stmt = (
            select(Video)
            .where(Video.id == id)
            .options(
                selectinload(Video.transcript)
                .selectinload(Video.transcript)
                .selectinload(Video.summary),
                selectinload(Video.project),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_youtube_id(self, youtube_video_id: str) -> Video | None:
        """Get video by YouTube video ID.

        Args:
            youtube_video_id: The YouTube video ID.

        Returns:
            Video instance or None.
        """
        return await self.get_by_field("youtube_video_id", youtube_video_id)

    async def get_by_youtube_ids(
        self, youtube_video_ids: list[str]
    ) -> Sequence[Video]:
        """Get videos by YouTube video IDs.

        Args:
            youtube_video_ids: List of YouTube video IDs.

        Returns:
            Sequence of Video instances.
        """
        if not youtube_video_ids:
            return []

        from sqlalchemy import or_

        conditions = [Video.youtube_video_id == ytid for ytid in youtube_video_ids]
        stmt = select(Video).where(or_(*conditions))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        status: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Video]:
        """List videos by project.

        Args:
            project_id: The project UUID.
            status: Optional status filter.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Sequence of Video instances.
        """
        filters: dict[str, Any] = {"project_id": project_id}
        if status:
            filters["status"] = status

        return await self.list_all(
            offset=offset,
            limit=limit,
            order_by="created_at",
            **filters,
        )

    async def list_by_status(
        self, status: str, offset: int = 0, limit: int = 100
    ) -> Sequence[Video]:
        """List videos by status.

        Args:
            status: The status to filter by.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Sequence of Video instances.
        """
        return await self.list(offset=offset, limit=limit, status=status)

    async def update_status(
        self, id: uuid.UUID, status: str, error_message: str | None = None
    ) -> Video | None:
        """Update video status.

        Args:
            id: The video UUID.
            status: New status value.
            error_message: Optional error message if status is 'failed'.

        Returns:
            Updated Video or None.
        """
        update_data: dict[str, Any] = {"status": status}
        if error_message:
            update_data["error_message"] = error_message

        return await self.update(id, **update_data)

    async def set_downloaded(self, id: uuid.UUID) -> Video | None:
        """Mark video as downloaded.

        Args:
            id: The video UUID.

        Returns:
            Updated Video or None.
        """
        from datetime import datetime, timezone

        return await self.update(
            id,
            status="downloaded",
            downloaded_at=datetime.now(timezone.utc),
        )

    async def set_processed(self, id: uuid.UUID) -> Video | None:
        """Mark video as processed.

        Args:
            id: The video UUID.

        Returns:
            Updated Video or None.
        """
        from datetime import datetime, timezone

        return await self.update(
            id,
            status="completed",
            processed_at=datetime.now(timezone.utc),
        )

    async def upsert_by_youtube_id(
        self, youtube_video_id: str, **kwargs: Any
    ) -> Video:
        """Insert or update video by YouTube ID.

        Args:
            youtube_video_id: The YouTube video ID.
            **kwargs: Field-value pairs for the video.

        Returns:
            The Video instance.
        """
        video = await self.get_by_youtube_id(youtube_video_id)
        if video:
            for key, value in kwargs.items():
                if hasattr(video, key):
                    setattr(video, key, value)
            await self.session.flush()
            await self.session.refresh(video)
            return video

        return await self.create(youtube_video_id=youtube_video_id, **kwargs)
