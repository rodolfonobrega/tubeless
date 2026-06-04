"""ConsolidatedSummary ORM model."""

import uuid
from typing import Optional

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.orm.base import BaseModel


class ConsolidatedSummary(BaseModel):
    """Project-level synthesis across all processed videos."""

    __tablename__ = "consolidated_summaries"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    key_themes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    consensus_points: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    differing_viewpoints: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    contradictions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    project = relationship("Project", back_populates="consolidated_summary")
