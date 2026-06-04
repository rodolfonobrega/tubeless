"""TranscriptChunk ORM model."""

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.orm.base import BaseModel


class TranscriptChunk(BaseModel):
    """TranscriptChunk model for storing chunked transcript segments."""

    __tablename__ = "transcript_chunks"

    transcript_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transcripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Chunk content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)  # Order in transcript

    # Token information
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Timestamp information (seconds)
    start_time: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    end_time: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)

    # Chapter this chunk belongs to (if video has chapters)
    chapter_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Source type: 'transcript' or 'comment'
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="transcript")

    # Contextual content: chunk enriched with video summary context for better embeddings
    contextual_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Embedding vector (pgvector)
    # Note: Using VECTOR type from pgvector extension
    # embedding: Mapped[Optional[list[float]]] = mapped_column(VECTOR(1536), nullable=True)

    # Relationships
    transcript = relationship("Transcript", back_populates="chunks")
    embeddings = relationship(
        "Embedding",
        back_populates="chunk",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<TranscriptChunk(id={self.id}, chunk_index={self.chunk_index})>"
