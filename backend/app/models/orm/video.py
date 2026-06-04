"""Video ORM model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.orm.base import BaseModel


class Video(BaseModel):
    """Video model representing a YouTube video."""

    __tablename__ = "videos"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # YouTube metadata
    youtube_video_id: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    channel_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    channel_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Video properties
    duration: Mapped[Optional[int]] = mapped_column(  # Duration in seconds
        nullable=True
    )
    view_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    like_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    comment_count: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Processing status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",  # pending, downloading, processing, completed, failed
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    downloaded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    project = relationship("Project", back_populates="videos")
    transcript = relationship(
        "Transcript",
        back_populates="video",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    summary = relationship(
        "VideoSummary",
        back_populates="video",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
