"""ChatMessage ORM model."""

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.orm.base import BaseModel


class ChatMessage(BaseModel):
    """ChatMessage model for storing individual chat messages."""

    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Message content
    role: Mapped[str] = mapped_column(  # user, assistant, system
        String(50), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # RAG context
    chunks_used: Mapped[Optional[str]] = mapped_column(  # JSON array of chunk IDs
        Text, nullable=True
    )

    # Token info
    token_count: Mapped[Optional[int]] = mapped_column(nullable=True)

    # RAG feedback: up / down / null
    feedback: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")
