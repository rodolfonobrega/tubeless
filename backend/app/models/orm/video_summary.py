"""VideoSummary ORM model."""

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.orm.base import BaseModel


class VideoSummary(BaseModel):
    """VideoSummary model for storing video-level summaries."""

    __tablename__ = "video_summaries"

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Summary content
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    key_points: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of strings

    # Model info
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Relationships
    video = relationship("Video", back_populates="summary")
