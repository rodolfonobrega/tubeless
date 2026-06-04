"""Transcript repository."""

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.orm.transcript import Transcript
from app.repositories.base import BaseRepository


class TranscriptRepository(BaseRepository[Transcript]):
    """Repository for Transcript model."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: The async database session.
        """
        super().__init__(Transcript, session)

    async def get_with_chunks(self, id: uuid.UUID) -> Transcript | None:
        """Get transcript with chunks.

        Args:
            id: The transcript UUID.

        Returns:
            Transcript with chunks loaded or None.
        """
        stmt = (
            select(Transcript)
            .where(Transcript.id == id)
            .options(selectinload(Transcript.chunks))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_video(self, video_id: uuid.UUID) -> Transcript | None:
        """Get transcript by video ID.

        Args:
            video_id: The video UUID.

        Returns:
            Transcript instance or None.
        """
        return await self.get_by_field("video_id", video_id)

    async def get_by_video_with_chunks(self, video_id: uuid.UUID) -> Transcript | None:
        """Get transcript by video ID with chunks.

        Args:
            video_id: The video UUID.

        Returns:
            Transcript with chunks loaded or None.
        """
        stmt = (
            select(Transcript)
            .where(Transcript.video_id == video_id)
            .options(selectinload(Transcript.chunks))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update_content(
        self,
        id: uuid.UUID,
        content: str,
        raw_content: str | None = None,
        language: str | None = None,
        word_count: int | None = None,
    ) -> Transcript | None:
        """Update transcript content.

        Args:
            id: The transcript UUID.
            content: The transcript text content.
            raw_content: The raw VTT/SRT content.
            language: The transcript language.
            word_count: The word count.

        Returns:
            Updated Transcript or None.
        """
        update_data: dict[str, str | int] = {"content": content}
        if raw_content is not None:
            update_data["raw_content"] = raw_content
        if language is not None:
            update_data["language"] = language
        if word_count is not None:
            update_data["word_count"] = word_count

        return await self.update(id, **update_data)
