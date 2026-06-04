"""Embedding repository."""

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.embedding import Embedding
from app.repositories.base import BaseRepository


class EmbeddingRepository(BaseRepository[Embedding]):
    """Repository for Embedding model."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: The async database session.
        """
        super().__init__(Embedding, session)

    async def get_by_transcript(
        self, transcript_id: uuid.UUID
    ) -> Sequence[Embedding]:
        """Get all embeddings for a transcript.

        Args:
            transcript_id: The transcript UUID.

        Returns:
            Sequence of Embedding instances.
        """
        stmt = (
            select(Embedding)
            .where(Embedding.transcript_id == transcript_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_chunk(self, chunk_id: uuid.UUID) -> Sequence[Embedding]:
        """Get embeddings for a specific chunk.

        Args:
            chunk_id: The chunk UUID.

        Returns:
            Sequence of Embedding instances.
        """
        return await self.list(chunk_id=chunk_id)

    async def delete_by_transcript(self, transcript_id: uuid.UUID) -> int:
        """Delete all embeddings for a transcript.

        Args:
            transcript_id: The transcript UUID.

        Returns:
            Number of embeddings deleted.
        """
        return await self.delete_by_field("transcript_id", transcript_id)

    async def create_embeddings(
        self, embeddings: list[dict[str, object]]
    ) -> Sequence[Embedding]:
        """Bulk create embeddings.

        Args:
            embeddings: List of embedding data dictionaries.

        Returns:
            Sequence of created Embedding instances.
        """
        return await self.create_many(embeddings)

    async def find_similar(
        self,
        query_vector: list[float],
        transcript_ids: list[uuid.UUID] | None = None,
        limit: int = 5,
        threshold: float = 0.7,
    ) -> Sequence[tuple[Embedding, float]]:
        """Find similar embeddings using cosine similarity.

        Args:
            query_vector: The query embedding vector.
            transcript_ids: Optional list of transcript IDs to filter by.
            limit: Maximum number of results.
            threshold: Minimum similarity score.

        Returns:
            Sequence of (Embedding, similarity_score) tuples.
        """
        # Build the SQL query for pgvector cosine similarity
        # 1 - (embedding <=> query_vector) gives cosine similarity
        sql = text("""
            SELECT id, transcript_id, chunk_id, vector, model_used, dimension,
                   created_at, updated_at,
                   1 - (vector <=> :query_vector) as similarity
            FROM embeddings
            WHERE 1 - (vector <=> :query_vector) >= :threshold
        """)

        params = {
            "query_vector": str(query_vector).replace("[", "[").replace("]", "]"),
            "threshold": threshold,
        }

        if transcript_ids:
            sql_str = str(sql)  # Get the SQL string
            # Add transcript filter
            transcript_ids_str = ",".join(f"'{tid}'" for tid in transcript_ids)
            sql = text(sql_str + f" AND transcript_id IN ({transcript_ids_str})")

        sql = text(str(sql) + f" ORDER BY vector <=> :query_vector LIMIT :limit")

        result = await self.session.execute(sql, {
            "query_vector": query_vector,
            "threshold": threshold,
            "limit": limit,
        })

        rows = result.fetchall()
        embeddings = []

        for row in rows:
            # Reconstruct Embedding objects
            embedding = Embedding(
                id=row.id,
                transcript_id=row.transcript_id,
                chunk_id=row.chunk_id,
                vector=row.vector,
                model_used=row.model_used,
                dimension=row.dimension,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            embeddings.append((embedding, row.similarity))

        return embeddings
