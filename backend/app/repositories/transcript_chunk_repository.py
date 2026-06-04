"""TranscriptChunk repository."""

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.transcript_chunk import TranscriptChunk
from app.repositories.base import BaseRepository


class TranscriptChunkRepository(BaseRepository[TranscriptChunk]):
    """Repository for TranscriptChunk model."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: The async database session.
        """
        super().__init__(TranscriptChunk, session)

    async def get_by_transcript(
        self, transcript_id: uuid.UUID
    ) -> Sequence[TranscriptChunk]:
        """Get all chunks for a transcript.

        Args:
            transcript_id: The transcript UUID.

        Returns:
            Sequence of TranscriptChunk instances ordered by chunk_index.
        """
        stmt = (
            select(TranscriptChunk)
            .where(TranscriptChunk.transcript_id == transcript_id)
            .order_by(TranscriptChunk.chunk_index)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_transcript_range(
        self,
        transcript_id: uuid.UUID,
        start_index: int,
        end_index: int,
    ) -> Sequence[TranscriptChunk]:
        """Get chunks for a transcript within an index range.

        Args:
            transcript_id: The transcript UUID.
            start_index: The starting chunk index.
            end_index: The ending chunk index (inclusive).

        Returns:
            Sequence of TranscriptChunk instances.
        """
        stmt = (
            select(TranscriptChunk)
            .where(
                TranscriptChunk.transcript_id == transcript_id,
                TranscriptChunk.chunk_index >= start_index,
                TranscriptChunk.chunk_index <= end_index,
            )
            .order_by(TranscriptChunk.chunk_index)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_transcript(self, transcript_id: uuid.UUID) -> int:
        """Delete all chunks for a transcript.

        Args:
            transcript_id: The transcript UUID.

        Returns:
            Number of chunks deleted.
        """
        return await self.delete_by_field("transcript_id", transcript_id)

    async def create_chunks(
        self, chunks: list[dict[str, object]]
    ) -> Sequence[TranscriptChunk]:
        """Bulk create transcript chunks.

        Args:
            chunks: List of chunk data dictionaries.

        Returns:
            Sequence of created TranscriptChunk instances.
        """
        return await self.create_many(chunks)

    async def get_chunk_by_index(
        self, transcript_id: uuid.UUID, chunk_index: int
    ) -> TranscriptChunk | None:
        """Get a specific chunk by index.

        Args:
            transcript_id: The transcript UUID.
            chunk_index: The chunk index.

        Returns:
            TranscriptChunk instance or None.
        """
        stmt = (
            select(TranscriptChunk)
            .where(
                TranscriptChunk.transcript_id == transcript_id,
                TranscriptChunk.chunk_index == chunk_index,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def count_by_transcript(self, transcript_id: uuid.UUID) -> int:
        """Count chunks for a transcript.

        Args:
            transcript_id: The transcript UUID.

        Returns:
            Number of chunks.
        """
        return await self.count(transcript_id=transcript_id)
