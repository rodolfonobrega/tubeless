"""Project ORM model."""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.orm.base import BaseModel


class ProjectStatus(str, enum.Enum):
    """Project status enumeration."""

    PENDING = "pending"
    FETCHING = "fetching"
    PROCESSING = "processing"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(BaseModel):
    """Project model for organizing videos and research."""

    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    query: Mapped[str] = mapped_column(String(500), nullable=False)  # Original search query
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",  # pending, processing, completed, failed
    )
    video_count: Mapped[int] = mapped_column(default=0, nullable=False)
    total_duration: Mapped[int] = mapped_column(  # Total duration in seconds
        default=0, nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    videos = relationship(
        "Video",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    consolidated_summary = relationship(
        "ConsolidatedSummary",
        back_populates="project",
        cascade="all, delete-orphan",
        primaryjoin="Project.id == foreign(ConsolidatedSummary.project_id)",
        lazy="selectin",
        uselist=False,
    )
