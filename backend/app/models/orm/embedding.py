"""Embedding ORM model."""

import uuid
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.orm.base import BaseModel


class Embedding(BaseModel):
    """Embedding model for storing vector embeddings."""

    __tablename__ = "embeddings"

    transcript_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transcripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transcript_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Embedding vector
    vector: Mapped[list[float]] = mapped_column(
        Vector(1536),  # Default dimension for OpenAI embeddings
        nullable=False,
    )

    # Model info
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)

    # Source type: 'transcript_chunk' or 'hypothetical_question'
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="transcript_chunk")

    # Content hash for cache identification
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # Dimension (for different embedding models)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    transcript = relationship("Transcript", back_populates="embeddings")
    chunk = relationship("TranscriptChunk", back_populates="embeddings")
