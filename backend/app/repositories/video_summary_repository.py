"""VideoSummary repository."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.orm.video_summary import VideoSummary
from app.repositories.base import BaseRepository


class VideoSummaryRepository(BaseRepository[VideoSummary]):
    """Repository for VideoSummary model."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: The async database session.
        """
        super().__init__(VideoSummary, session)

    async def get_by_video(self, video_id: uuid.UUID) -> VideoSummary | None:
        """Get summary by video ID.

        Args:
            video_id: The video UUID.

        Returns:
            VideoSummary instance or None.
        """
        return await self.get_by_field("video_id", video_id)

    async def upsert_by_video(
        self,
        video_id: uuid.UUID,
        content: str,
        title: str | None = None,
        key_points: str | None = None,
        model_used: str | None = None,
        token_count: int | None = None,
    ) -> VideoSummary:
        """Insert or update video summary.

        Args:
            video_id: The video UUID.
            content: The summary content.
            title: Optional summary title.
            key_points: Optional JSON array of key points.
            model_used: The model used for generation.
            token_count: The token count.

        Returns:
            The VideoSummary instance.
        """
        summary = await self.get_by_video(video_id)
        data: dict[str, str | int] = {"content": content}
        if title is not None:
            data["title"] = title
        if key_points is not None:
            data["key_points"] = key_points
        if model_used is not None:
            data["model_used"] = model_used
        if token_count is not None:
            data["token_count"] = token_count

        if summary:
            for key, value in data.items():
                setattr(summary, key, value)
            await self.session.flush()
            await self.session.refresh(summary)
            return summary

        return await self.create(video_id=video_id, **data)
