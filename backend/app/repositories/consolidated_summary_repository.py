"""ConsolidatedSummary repository."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.consolidated_summary import ConsolidatedSummary
from app.repositories.base import BaseRepository


class ConsolidatedSummaryRepository(BaseRepository[ConsolidatedSummary]):
    """Repository for ConsolidatedSummary model."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: The async database session.
        """
        super().__init__(ConsolidatedSummary, session)

    async def create_summary(
        self,
        content: str,
        title: str | None = None,
        key_topics: str | None = None,
        synthesis_notes: str | None = None,
        model_used: str | None = None,
        token_count: int | None = None,
        source_video_count: int = 0,
    ) -> ConsolidatedSummary:
        """Create a new consolidated summary.

        Args:
            content: The summary content.
            title: Optional summary title.
            key_topics: Optional JSON array of key topics.
            synthesis_notes: Optional synthesis notes.
            model_used: The model used for generation.
            token_count: The token count.
            source_video_count: Number of source videos.

        Returns:
            The created ConsolidatedSummary instance.
        """
        return await self.create(
            content=content,
            title=title,
            key_topics=key_topics,
            synthesis_notes=synthesis_notes,
            model_used=model_used,
            token_count=token_count,
            source_video_count=source_video_count,
        )
