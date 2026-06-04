"""Chat API endpoints for RAG."""

import json
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.core.db import get_session_context as get_session
from app.models.orm import ChatMessage, ChatSession
from app.services.rag_service import RAGService
from pydantic import BaseModel

router = APIRouter()


class CreateSessionRequest(BaseModel):
    project_id: str
    title: str | None = None


@router.post("/sessions")
async def create_chat_session(request: CreateSessionRequest):
    """Create a new chat session."""
    async with get_session() as session:
        session_obj = ChatSession(
            project_id=uuid.UUID(request.project_id),
            title=request.title or "New Chat",
        )
        session.add(session_obj)
        await session.commit()
        await session.refresh(session_obj)

        return {
            "id": str(session_obj.id),
            "project_id": str(session_obj.project_id),
            "title": session_obj.title,
        }


class MessageRequest(BaseModel):
    message: str
    video_ids: list[str] | None = None


@router.post("/projects/{project_id}/send")
async def send_chat_message(project_id: uuid.UUID, request: MessageRequest):
    """Send a message and get streaming response."""

    async def generate():
        async with get_session() as session:
            # Get or create session
            result = await session.execute(
                select(ChatSession)
                .where(ChatSession.project_id == project_id)
                .order_by(ChatSession.created_at.desc())
                .limit(1)
            )
            chat_session = result.scalar_one_or_none()

            if not chat_session:
                chat_session = ChatSession(project_id=project_id, title="Chat")
                session.add(chat_session)
                await session.flush()

            # Fetch conversation history (last 10 messages)
            history_result = await session.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == chat_session.id)
                .order_by(ChatMessage.created_at.desc())
                .limit(10)
            )
            history = [
                {"role": m.role, "content": m.content}
                for m in reversed(history_result.scalars().all())
            ]

            # Store user message
            user_message = ChatMessage(
                session_id=chat_session.id,
                role="user",
                content=request.message,
            )
            session.add(user_message)
            await session.commit()

            # Get RAG response
            rag_service = RAGService(session)

            response_text = ""
            async for item in rag_service.stream_query(
                request.message, project_id, history=history, video_ids=request.video_ids
            ):
                if isinstance(item, dict) and "__sources__" in item:
                    yield f"data: {json.dumps({'sources': item['__sources__']})}\n\n"
                else:
                    response_text += item
                    yield f"data: {json.dumps({'content': item})}\n\n"

            yield "data: [DONE]\n\n"

            # Store assistant message
            assistant_message = ChatMessage(
                session_id=chat_session.id,
                role="assistant",
                content=response_text,
            )
            session.add(assistant_message)
            await session.commit()

    return StreamingResponse(generate(), media_type="text/event-stream")


class FeedbackRequest(BaseModel):
    feedback: str  # "up" or "down"


@router.post("/messages/{message_id}/feedback")
async def add_feedback(message_id: uuid.UUID, request: FeedbackRequest):
    """Add up/down feedback to an assistant message."""
    if request.feedback not in {"up", "down"}:
        raise HTTPException(status_code=400, detail="feedback must be 'up' or 'down'")

    async with get_session() as session:
        result = await session.execute(
            select(ChatMessage).where(ChatMessage.id == message_id)
        )
        message = result.scalar_one_or_none()
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        message.feedback = request.feedback
        await session.commit()
        return {"status": "ok", "message_id": str(message_id), "feedback": request.feedback}


@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: uuid.UUID):
    """Get all messages for a session."""
    async with get_session() as session:
        result = await session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        messages = result.scalars().all()

        return {
            "data": [
                {
                    "id": str(m.id),
                    "role": m.role,
                    "content": m.content,
                    "sources": json.loads(m.chunks_used) if m.chunks_used else None,
                    "feedback": m.feedback,
                }
                for m in messages
            ]
        }
