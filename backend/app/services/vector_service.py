"""Vector service for pgvector operations."""

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.orm.embedding import Embedding
from app.models.orm.transcript_chunk import TranscriptChunk
from app.models.orm.video import Video

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Represents a similarity search result."""

    chunk: TranscriptChunk
    similarity: float
    video_title: str | None = None
    video_youtube_id: str | None = None
    rerank_score: float | None = None


class VectorService:
    """Service for vector similarity search using pgvector."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the vector service.

        Args:
            session: The async database session.
        """
        self.session = session
        self.dimension = settings.vector_dimension

    async def find_embedding_by_hash(
        self,
        content_hash: str,
        model_used: str,
    ) -> list[float] | None:
        """Find a cached embedding by content hash and model."""
        result = await self.session.execute(
            select(Embedding.vector)
            .where(Embedding.content_hash == content_hash)
            .where(Embedding.model_used == model_used)
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return list(row) if row is not None else None

    async def store_embedding(
        self,
        content_id: uuid.UUID,
        content_type: str,
        embedding: list[float],
        model_used: str,
        content_hash: str | None = None,
        source_type: str = "transcript_chunk",
    ) -> Embedding:
        """Store a vector embedding for a transcript chunk."""
        chunk_result = await self.session.execute(
            select(TranscriptChunk).where(TranscriptChunk.id == content_id)
        )
        chunk = chunk_result.scalar_one()

        embedding_record = Embedding(
            transcript_id=chunk.transcript_id,
            chunk_id=content_id,
            vector=embedding,
            model_used=model_used,
            dimension=len(embedding),
            content_hash=content_hash,
            source_type=source_type,
        )
        self.session.add(embedding_record)
        await self.session.flush()
        return embedding_record

    async def find_similar_chunks(
        self,
        query_vector: list[float],
        transcript_ids: list[str] | None = None,
        limit: int = 5,
        threshold: float | None = None,
    ) -> list[tuple[TranscriptChunk, float]]:
        """Find similar transcript chunks using vector similarity.

        Args:
            query_vector: The query embedding vector.
            transcript_ids: Optional list of transcript IDs to filter by.
            limit: Maximum number of results to return.
            threshold: Minimum similarity score (0-1). Defaults to settings.

        Returns:
            List of (TranscriptChunk, similarity_score) tuples.
        """
        threshold_value = threshold or settings.similarity_threshold

        # Build SQL query for cosine similarity search
        # Using <=> operator for cosine distance (lower is better)
        # Convert to similarity: 1 - cosine_distance
        query_sql = """
            SELECT
                tc.id,
                tc.transcript_id,
                tc.chunk_index,
                tc.content,
                tc.token_count,
                tc.start_time,
                tc.end_time,
                tc.created_at,
                tc.updated_at,
                1 - (e.vector <=> :query_vector) as similarity
            FROM transcript_chunks tc
            JOIN embeddings e ON tc.id = e.chunk_id
            WHERE 1 - (e.vector <=> :query_vector) >= :threshold
        """

        params: dict[str, Any] = {
            "query_vector": str(query_vector),
            "threshold": threshold_value,
            "limit": limit,
        }

        # Add transcript filter if provided
        if transcript_ids:
            transcript_ids_str = ", ".join(f"'{tid}'" for tid in transcript_ids)
            query_sql += f" AND tc.transcript_id IN ({transcript_ids_str})"

        # Add order and limit
        query_sql += " ORDER BY e.vector <=> :query_vector LIMIT :limit"

        try:
            result = await self.session.execute(text(query_sql), params)
            rows = result.fetchall()

            chunks = []
            for row in rows:
                chunk = TranscriptChunk(
                    id=row[0],
                    transcript_id=row[1],
                    chunk_index=row[2],
                    content=row[3],
                    token_count=row[4],
                    start_time=row[5],
                    end_time=row[6],
                    created_at=row[7],
                    updated_at=row[8],
                )
                similarity = float(row[9])
                chunks.append((chunk, similarity))

            return chunks

        except Exception as e:
            logger.error(f"Vector similarity search failed: {e}")
            return []

    async def find_similar_by_project(
        self,
        query_vector: list[float],
        project_id: str,
        limit: int = 5,
        threshold: float | None = None,
    ) -> list[SearchResult]:
        """Find similar chunks within a project.

        Args:
            query_vector: The query embedding vector.
            project_id: The project ID to search within.
            limit: Maximum number of results.
            threshold: Minimum similarity score.

        Returns:
            List of SearchResult objects with chunk, similarity, and video info.
        """
        threshold_value = threshold or settings.similarity_threshold

        # Join through videos to get project's transcripts
        query_sql = """
            SELECT
                tc.id,
                tc.transcript_id,
                tc.chunk_index,
                tc.content,
                tc.token_count,
                tc.start_time,
                tc.end_time,
                v.title as video_title,
                v.youtube_video_id,
                1 - (e.vector <=> :query_vector) as similarity,
                tc.source_type
            FROM transcript_chunks tc
            JOIN embeddings e ON tc.id = e.chunk_id
            JOIN transcripts t ON tc.transcript_id = t.id
            JOIN videos v ON t.video_id = v.id
            WHERE v.project_id = :project_id
            AND 1 - (e.vector <=> :query_vector) >= :threshold
            ORDER BY e.vector <=> :query_vector
            LIMIT :limit
        """

        params = {
            "query_vector": str(query_vector),
            "project_id": project_id,
            "threshold": threshold_value,
            "limit": limit,
        }

        try:
            result = await self.session.execute(text(query_sql), params)
            rows = result.fetchall()

            results = []
            for row in rows:
                # Columns: 0=id, 1=transcript_id, 2=chunk_index, 3=content,
                #          4=token_count, 5=start_time, 6=end_time,
                #          7=video_title, 8=youtube_video_id, 9=similarity, 10=source_type
                chunk = TranscriptChunk(
                    id=row[0],
                    transcript_id=row[1],
                    chunk_index=row[2],
                    content=row[3],
                    token_count=row[4],
                    start_time=row[5],
                    end_time=row[6],
                    source_type=row[10],
                )
                similarity = float(row[9])
                results.append(SearchResult(
                    chunk=chunk,
                    similarity=similarity,
                    video_title=row[7],
                    video_youtube_id=row[8],
                ))

            return results

        except Exception as e:
            logger.error(f"Project vector search failed: {e}")
            return []

    async def get_chunks_for_embedding(
        self,
        transcript_id: str,
        limit: int = 100,
    ) -> list[TranscriptChunk]:
        """Get chunks that need embeddings.

        Args:
            transcript_id: The transcript ID.
            limit: Maximum chunks to return.

        Returns:
            List of TranscriptChunk objects without embeddings.
        """
        # Find chunks that don't have embeddings yet
        query_sql = """
            SELECT tc.id, tc.transcript_id, tc.chunk_index, tc.content,
                   tc.token_count, tc.start_time, tc.end_time,
                   tc.created_at, tc.updated_at
            FROM transcript_chunks tc
            LEFT JOIN embeddings e ON tc.id = e.chunk_id
            WHERE tc.transcript_id = :transcript_id
            AND e.id IS NULL
            ORDER BY tc.chunk_index
            LIMIT :limit
        """

        try:
            result = await self.session.execute(text(query_sql), {
                "transcript_id": transcript_id,
                "limit": limit,
            })
            rows = result.fetchall()

            chunks = []
            for row in rows:
                chunk = TranscriptChunk(
                    id=row[0],
                    transcript_id=row[1],
                    chunk_index=row[2],
                    content=row[3],
                    token_count=row[4],
                    start_time=row[5],
                    end_time=row[6],
                    created_at=row[7],
                    updated_at=row[8],
                )
                chunks.append(chunk)

            return chunks

        except Exception as e:
            logger.error(f"Failed to get chunks for embedding: {e}")
            return []

    async def hybrid_search(
        self,
        query_vector: list[float],
        query_text: str,
        project_id: str,
        limit: int = 5,
        threshold: float | None = None,
        video_ids: list[str] | None = None,
        rerank_top_k: int | None = None,
    ) -> list[SearchResult]:
        """Hybrid search combining vector similarity and full-text search via RRF.

        Uses Reciprocal Rank Fusion (k=60) to merge rankings from:
        - Vector search (cosine similarity via pgvector)
        - Full-text search (tsvector GIN index, language-agnostic 'simple' dictionary)
        
        If rerank_top_k is provided, fetches extra candidates for reranking
        and returns exactly rerank_top_k results after cross-encoder reranking.
        """
        threshold_value = threshold or settings.similarity_threshold
        # Fetch extra candidates when reranking is enabled
        fetch_limit = rerank_top_k * 10 if rerank_top_k else limit * 3

        video_filter = "AND v.youtube_video_id = ANY(:video_ids)" if video_ids else ""

        vector_sql = f"""
            SELECT
                tc.id,
                tc.transcript_id,
                tc.chunk_index,
                tc.content,
                tc.token_count,
                tc.start_time,
                tc.end_time,
                v.title as video_title,
                v.youtube_video_id,
                1 - (e.vector <=> :query_vector) as similarity,
                tc.source_type
            FROM transcript_chunks tc
            JOIN embeddings e ON tc.id = e.chunk_id
            JOIN transcripts t ON tc.transcript_id = t.id
            JOIN videos v ON t.video_id = v.id
            WHERE v.project_id = :project_id
            AND 1 - (e.vector <=> :query_vector) >= :threshold
            {video_filter}
            ORDER BY e.vector <=> :query_vector
            LIMIT :limit
        """

        fts_sql = f"""
            SELECT
                tc.id,
                tc.transcript_id,
                tc.chunk_index,
                tc.content,
                tc.token_count,
                tc.start_time,
                tc.end_time,
                v.title as video_title,
                v.youtube_video_id,
                ts_rank_cd(to_tsvector('simple', tc.content),
                           websearch_to_tsquery('simple', :query_text)) as fts_rank,
                tc.source_type
            FROM transcript_chunks tc
            JOIN transcripts t ON tc.transcript_id = t.id
            JOIN videos v ON t.video_id = v.id
            WHERE v.project_id = :project_id
            AND to_tsvector('simple', tc.content) @@ websearch_to_tsquery('simple', :query_text)
            {video_filter}
            ORDER BY fts_rank DESC
            LIMIT :limit
        """

        params_vector: dict = {
            "query_vector": str(query_vector),
            "project_id": project_id,
            "threshold": threshold_value,
            "limit": fetch_limit,
        }
        params_fts: dict = {
            "query_text": query_text,
            "project_id": project_id,
            "limit": fetch_limit,
        }
        if video_ids:
            params_vector["video_ids"] = video_ids
            params_fts["video_ids"] = video_ids

        try:
            vector_result = await self.session.execute(text(vector_sql), params_vector)
            vector_rows = vector_result.fetchall()
        except Exception as e:
            logger.error(f"Vector search failed in hybrid: {e}")
            vector_rows = []

        try:
            fts_result = await self.session.execute(text(fts_sql), params_fts)
            fts_rows = fts_result.fetchall()
        except Exception as e:
            logger.warning(f"FTS search failed in hybrid (falling back to vector only): {e}")
            fts_rows = []

        # RRF fusion
        k = 60
        rrf_scores: dict[str, float] = {}
        chunk_data: dict[str, tuple] = {}

        for rank, row in enumerate(vector_rows):
            chunk_id = str(row[0])
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
            chunk_data[chunk_id] = row

        for rank, row in enumerate(fts_rows):
            chunk_id = str(row[0])
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
            if chunk_id not in chunk_data:
                chunk_data[chunk_id] = row

        sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)[:limit]

        results = []
        for chunk_id in sorted_ids:
            row = chunk_data[chunk_id]
            chunk = TranscriptChunk(
                id=row[0],
                transcript_id=row[1],
                chunk_index=row[2],
                content=row[3],
                token_count=row[4],
                start_time=row[5],
                end_time=row[6],
                source_type=row[10],
            )
            results.append(SearchResult(
                chunk=chunk,
                similarity=rrf_scores[chunk_id],
                video_title=row[7],
                video_youtube_id=row[8],
            ))

        return results

    def cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector.
            vec2: Second vector.

        Returns:
            Cosine similarity score (0-1).
        """
        if len(vec1) != len(vec2):
            raise ValueError("Vectors must have the same dimension")

        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)
