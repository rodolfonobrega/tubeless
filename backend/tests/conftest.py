"""Shared fixtures for all tests."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.services.transcript_service import TranscriptSegment


# ---------------------------------------------------------------------------
# Transcript segment helpers
# ---------------------------------------------------------------------------

def make_segment(text: str, start: float = 0.0, end: float = 1.0) -> TranscriptSegment:
    return TranscriptSegment(text=text, start=start, end=end)


def make_segments(texts: list[str], duration_each: float = 5.0) -> list[TranscriptSegment]:
    segs = []
    for i, text in enumerate(texts):
        segs.append(TranscriptSegment(text=text, start=i * duration_each, end=(i + 1) * duration_each))
    return segs


# ---------------------------------------------------------------------------
# LLM response factory
# ---------------------------------------------------------------------------

def make_llm_response(content: str) -> MagicMock:
    """Build a minimal litellm-style response object."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    return response


# ---------------------------------------------------------------------------
# DB / project mocks
# ---------------------------------------------------------------------------

def make_project(
    name: str = "Test Project",
    query: str = "test query",
    status: str = "pending",
    video_count: int = 1,
    total_duration: int = 0,
) -> MagicMock:
    proj = MagicMock()
    proj.id = uuid.uuid4()
    proj.name = name
    proj.description = None
    proj.query = query
    proj.status = status
    proj.video_count = video_count
    proj.total_duration = total_duration
    proj.error_message = None
    proj.created_at = datetime(2026, 1, 1, 12, 0, 0)
    proj.updated_at = datetime(2026, 1, 1, 12, 0, 0)
    return proj


# ---------------------------------------------------------------------------
# FastAPI TestClient with mocked lifespan
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def client(mock_session):
    from app.main import app
    from app.core.db import get_session

    async def override_get_session():
        yield mock_session

    app.dependency_overrides[get_session] = override_get_session

    # Mock session maker context manager to yield mock_session
    mock_session_maker = MagicMock()
    mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_maker.return_value.__aexit__ = AsyncMock()

    with patch("app.main.init_db", AsyncMock()), \
         patch("app.main.close_db", AsyncMock()), \
         patch("app.main.async_session_maker", mock_session_maker), \
         patch("app.core.effective_settings.load_effective_settings", AsyncMock(return_value={})):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

    app.dependency_overrides.clear()
