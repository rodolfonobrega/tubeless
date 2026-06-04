"""Videos API endpoints."""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models.orm.video import Video
from app.repositories.video_repository import VideoRepository
from app.repositories.transcript_repository import TranscriptRepository
from app.repositories.transcript_chunk_repository import TranscriptChunkRepository
from app.repositories.video_summary_repository import VideoSummaryRepository
from app.services.transcript_service import TranscriptService
from app.services.chunking_service import ChunkingService
from app.services.summarization_service import SummarizationService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)
router = APIRouter()


class VideoResponse(BaseModel):
    """Response model for video data."""

    id: str
    project_id: str
    youtube_video_id: str
    title: str | None
    description: str | None
    channel_title: str | None
    thumbnail_url: str | None
    duration: int | None
    view_count: int | None
    status: str
    downloaded_at: str | None
    processed_at: str | None


class VideoListResponse(BaseModel):
    """Response model for video list."""

    videos: list[VideoResponse]
    total: int


class TranscriptResponse(BaseModel):
    """Response model for transcript data."""

    id: str
    video_id: str
    language: str | None
    content: str
    word_count: int


class VideoSummaryResponse(BaseModel):
    """Response model for video summary."""

    id: str
    video_id: str
    title: str | None
    content: str
    key_points: list[str] | None


@router.get("", response_model=VideoListResponse)
async def list_videos(
    project_id: str | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
) -> VideoListResponse:
    """List videos with optional filtering.

    Args:
        project_id: Optional project ID filter.
        status: Optional status filter.
        offset: Number of records to skip.
        limit: Maximum number of records to return.
        session: Database session.

    Returns:
        List of videos.
    """
    video_repo = VideoRepository(session)

    if project_id:
        try:
            project_uuid = uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project ID format",
            )
        videos = await video_repo.list_by_project(project_uuid, status=status, offset=offset, limit=limit)
    else:
        videos = await video_repo.list_all(offset=offset, limit=limit, status=status)

    return VideoListResponse(
        videos=[_video_to_response(v) for v in videos],
        total=len(videos),
    )


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    session: AsyncSession = Depends(get_session),
) -> VideoResponse:
    """Get a video by ID.

    Args:
        video_id: The video UUID.
        session: Database session.

    Returns:
        The video.

    Raises:
        HTTPException: If video not found.
    """
    video_repo = VideoRepository(session)

    try:
        video_uuid = uuid.UUID(video_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid video ID format",
        )

    video = await video_repo.get(video_uuid)

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    return _video_to_response(video)


@router.post("/{video_id}/process", status_code=status.HTTP_202_ACCEPTED)
async def process_video(
    video_id: str,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Process a video (download transcript, chunk, summarize, embed).

    Args:
        video_id: The video UUID.
        background_tasks: FastAPI background tasks.
        session: Database session.

    Returns:
        Processing status message.

    Raises:
        HTTPException: If video not found or already processed.
    """
    video_repo = VideoRepository(session)

    try:
        video_uuid = uuid.UUID(video_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid video ID format",
        )

    video = await video_repo.get(video_uuid)

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    if video.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video already processed",
        )

    # Update status to processing
    await video_repo.update_status(video_uuid, "processing")
    await session.commit()

    # Queue background processing
    background_tasks.add_task(
        _process_video_task,
        str(video_uuid),
        str(video.youtube_video_id),
        video.title,
    )

    return {"status": "processing", "message": "Video processing started"}


@router.get("/{video_id}/transcript", response_model=TranscriptResponse)
async def get_video_transcript(
    video_id: str,
    session: AsyncSession = Depends(get_session),
) -> TranscriptResponse:
    """Get transcript for a video.

    Args:
        video_id: The video UUID.
        session: Database session.

    Returns:
        The transcript.

    Raises:
        HTTPException: If transcript not found.
    """
    transcript_repo = TranscriptRepository(session)

    try:
        video_uuid = uuid.UUID(video_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid video ID format",
        )

    transcript = await transcript_repo.get_by_video(video_uuid)

    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found",
        )

    return TranscriptResponse(
        id=str(transcript.id),
        video_id=str(transcript.video_id),
        language=transcript.language,
        content=transcript.content or "",
        word_count=transcript.word_count or 0,
    )


@router.get("/{video_id}/summary", response_model=VideoSummaryResponse)
async def get_video_summary(
    video_id: str,
    session: AsyncSession = Depends(get_session),
) -> VideoSummaryResponse:
    """Get summary for a video.

    Args:
        video_id: The video UUID.
        session: Database session.

    Returns:
        The video summary.

    Raises:
        HTTPException: If summary not found.
    """
    summary_repo = VideoSummaryRepository(session)

    try:
        video_uuid = uuid.UUID(video_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid video ID format",
        )

    summary = await summary_repo.get_by_video(video_uuid)

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary not found",
        )

    import json

    key_points = None
    if summary.key_points:
        try:
            key_points = json.loads(summary.key_points)
        except json.JSONDecodeError:
            pass

    return VideoSummaryResponse(
        id=str(summary.id),
        video_id=str(summary.video_id),
        title=summary.title,
        content=summary.content,
        key_points=key_points,
    )


async def _process_video_task(
    video_uuid: str,
    youtube_video_id: str,
    video_title: str,
) -> None:
    """Background task to process a video.

    Args:
        video_uuid: The video UUID.
        youtube_video_id: The YouTube video ID.
        video_title: The video title.
    """
    # This would run in a background task with its own session
    # For now, just log the action
    logger.info(f"Processing video {video_uuid} ({video_title})")


def _video_to_response(video: Video) -> VideoResponse:
    """Convert Video model to response.

    Args:
        video: The Video model.

    Returns:
        VideoResponse instance.
    """
    return VideoResponse(
        id=str(video.id),
        project_id=str(video.project_id),
        youtube_video_id=video.youtube_video_id,
        title=video.title,
        description=video.description,
        channel_title=video.channel_title,
        thumbnail_url=video.thumbnail_url,
        duration=video.duration,
        view_count=video.view_count,
        status=video.status,
        downloaded_at=video.downloaded_at.isoformat() if video.downloaded_at else None,
        processed_at=video.processed_at.isoformat() if video.processed_at else None,
    )
