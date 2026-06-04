"""Embedding service with caching support."""

import hashlib
import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Embedding
from app.services.llm_service import LLMService
from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and managing embeddings with cache."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.llm_service = LLMService()
        self.vector_service = VectorService(session)

    def _content_hash(self, text: str) -> str:
        """Generate SHA-256 hash of text for cache lookup."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def _get_cached_embedding(
        self, content_hash: str, model_used: str
    ) -> list[float] | None:
        """Look up cached embedding by content hash and model."""
        return await self.vector_service.find_embedding_by_hash(
            content_hash=content_hash,
            model_used=model_used,
        )

    async def generate_and_store(
        self,
        content_id: uuid.UUID,
        content_type: str,
        text: str,
    ) -> Embedding:
        """Generate embedding for text and store it (with cache)."""
        content_hash = self._content_hash(text)
        cached = await self._get_cached_embedding(content_hash, self.llm_service.model)
        if cached:
            return await self.vector_service.store_embedding(
                content_id=content_id,
                content_type=content_type,
                embedding=cached,
                model_used=self.llm_service.model,
                content_hash=content_hash,
            )

        embedding = await self.llm_service.generate_embedding(text)
        return await self.vector_service.store_embedding(
            content_id=content_id,
            content_type=content_type,
            embedding=embedding,
            model_used=self.llm_service.model,
            content_hash=content_hash,
        )

    async def generate_batch_and_store(
        self,
        items: list[tuple[uuid.UUID, str]],
        content_type: str,
    ) -> list[Embedding]:
        """Generate embeddings for multiple texts and store them (with cache)."""
        if not items:
            return []

        # Check cache for each item
        texts = []
        hashes = []
        cached_embeddings: dict[str, list[float]] = {}

        for _, text in items:
            h = self._content_hash(text)
            hashes.append(h)
            cached = await self._get_cached_embedding(h, self.llm_service.model)
            if cached:
                cached_embeddings[h] = cached
            else:
                texts.append(text)

        # Generate embeddings only for uncached texts
        generated: dict[str, list[float]] = {}
        if texts:
            batch_embeddings = await self.llm_service.generate_embeddings_batch(texts)
            for text, emb in zip(texts, batch_embeddings):
                h = self._content_hash(text)
                generated[h] = emb

        records = []
        for (content_id, text), h in zip(items, hashes):
            embedding = cached_embeddings.get(h) or generated.get(h)
            if not embedding:
                logger.warning(f"Missing embedding for hash {h}, regenerating")
                embedding = await self.llm_service.generate_embedding(text)
                generated[h] = embedding

            record = await self.vector_service.store_embedding(
                content_id=content_id,
                content_type=content_type,
                embedding=embedding,
                model_used=self.llm_service.model,
                content_hash=h,
            )
            records.append(record)

        return records
