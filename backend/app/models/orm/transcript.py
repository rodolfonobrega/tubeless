"""Transcript ORM model."""

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.orm.base import BaseModel


class Transcript(BaseModel):
    """Transcript model containing the full video transcript."""

    __tablename__ = "transcripts"

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Transcript content
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Full text
    raw_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # VTT/SRT format

    word_count: Mapped[Optional[int]] = mapped_column(nullable=True, default=0)

    # Relationships
    video = relationship("Video", back_populates="transcript")
    chunks = relationship(
        "TranscriptChunk",
        back_populates="transcript",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    embeddings = relationship(
        "Embedding",
        back_populates="transcript",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
