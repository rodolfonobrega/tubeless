"""Chat session and message repository."""

import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import Select, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.orm.chat_message import ChatMessage
from app.models.orm.chat_session import ChatSession
from app.repositories.base import BaseRepository


class ChatSessionRepository(BaseRepository[ChatSession]):
    """Repository for ChatSession model."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: The async database session.
        """
        super().__init__(ChatSession, session)

    async def get_with_messages(self, id: uuid.UUID) -> ChatSession | None:
        """Get chat session with all messages.

        Args:
            id: The session UUID.

        Returns:
            ChatSession with messages loaded or None.
        """
        stmt = (
            select(ChatSession)
            .where(ChatSession.id == id)
            .options(selectinload(ChatSession.messages))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_project(
        self, project_id: uuid.UUID, offset: int = 0, limit: int = 50
    ) -> Sequence[ChatSession]:
        """List chat sessions for a project.

        Args:
            project_id: The project UUID.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Sequence of ChatSession instances.
        """
        return await self.list(
            offset=offset,
            limit=limit,
            project_id=project_id,
            order_by="created_at",
        )

    async def create_session(
        self,
        project_id: uuid.UUID,
        title: str | None = None,
        model_used: str | None = None,
    ) -> ChatSession:
        """Create a new chat session.

        Args:
            project_id: The project UUID.
            title: Optional session title.
            model_used: Optional model name.

        Returns:
            The created ChatSession instance.
        """
        return await self.create(
            project_id=project_id,
            title=title,
            model_used=model_used,
        )


class ChatMessageRepository(BaseRepository[ChatMessage]):
    """Repository for ChatMessage model."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: The async database session.
        """
        super().__init__(ChatMessage, session)

    async def list_by_session(
        self,
        session_id: uuid.UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ChatMessage]:
        """List messages for a session.

        Args:
            session_id: The session UUID.
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Sequence of ChatMessage instances ordered by created_at.
        """
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_message(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
        chunks_used: list[str] | None = None,
        token_count: int | None = None,
    ) -> ChatMessage:
        """Create a new chat message.

        Args:
            session_id: The session UUID.
            role: The message role (user, assistant, system).
            content: The message content.
            chunks_used: Optional list of chunk IDs used for RAG.
            token_count: Optional token count.

        Returns:
            The created ChatMessage instance.
        """
        import json

        chunks_used_json = json.dumps(chunks_used) if chunks_used else None

        return await self.create(
            session_id=session_id,
            role=role,
            content=content,
            chunks_used=chunks_used_json,
            token_count=token_count,
        )

    async def delete_by_session(self, session_id: uuid.UUID) -> int:
        """Delete all messages for a session.

        Args:
            session_id: The session UUID.

        Returns:
            Number of messages deleted.
        """
        return await self.delete_by_field("session_id", session_id)
