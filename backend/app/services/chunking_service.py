"""Chunking service for splitting text into manageable pieces."""

import logging
from typing import Any

from app.core.config import get_settings
from app.services.llm_service import LLMService
from app.services.transcript_service import TranscriptSegment

settings = get_settings()
logger = logging.getLogger(__name__)


class Chunk:
    def __init__(
        self,
        content: str,
        start_timestamp: float,
        end_timestamp: float,
        chunk_index: int,
        token_count: int,
        metadata: dict[str, Any] | None = None,
        chapter_title: str | None = None,
    ):
        self.content = content
        self.start_timestamp = start_timestamp
        self.end_timestamp = end_timestamp
        self.chunk_index = chunk_index
        self.token_count = token_count
        self.metadata = metadata or {}
        self.chapter_title = chapter_title


class ChunkingService:
    def __init__(self) -> None:
        self.llm_service = LLMService()
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
        self.max_chunk_size = settings.max_chunk_size

    def chunk_transcript(
        self,
        segments: list[TranscriptSegment],
        chapters: list[dict] | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> list[Chunk]:
        """Chunk transcript by chapters if available, else by token count."""
        if chapters:
            return self._chunk_by_chapters(segments, chapters)
        return self._chunk_by_tokens(segments, chunk_size, chunk_overlap)

    def _chunk_by_chapters(
        self,
        segments: list[TranscriptSegment],
        chapters: list[dict],
    ) -> list[Chunk]:
        """Create one chunk per chapter. Subdivides if chapter exceeds max_chunk_size."""
        chunks: list[Chunk] = []
        chunk_idx = 0

        for chapter in chapters:
            start = chapter.get("start_time", 0.0)
            end = chapter.get("end_time", float("inf"))
            title = chapter.get("title", "")

            chapter_segments = [s for s in segments if s.start >= start and s.start < end]
            if not chapter_segments:
                continue

            tokens = self.llm_service.count_tokens(" ".join(s.text for s in chapter_segments))

            if tokens <= self.max_chunk_size:
                content = " ".join(s.text for s in chapter_segments)
                chunks.append(Chunk(
                    content=content,
                    start_timestamp=chapter_segments[0].start,
                    end_timestamp=chapter_segments[-1].end,
                    chunk_index=chunk_idx,
                    token_count=tokens,
                    chapter_title=title,
                ))
                chunk_idx += 1
            else:
                # Chapter too large — subdivide with token-based chunking
                sub_chunks = self._chunk_by_tokens(chapter_segments)
                for sub in sub_chunks:
                    sub.chunk_index = chunk_idx
                    sub.chapter_title = title
                    chunks.append(sub)
                    chunk_idx += 1

        return chunks

    def _chunk_by_tokens(
        self,
        segments: list[TranscriptSegment],
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> list[Chunk]:
        chunk_size = chunk_size or self.chunk_size
        chunk_overlap = chunk_overlap or self.chunk_overlap

        chunks = []
        current_segments: list[TranscriptSegment] = []
        current_tokens = 0
        chunk_idx = 0

        for segment in segments:
            seg_tokens = self.llm_service.count_tokens(segment.text)

            if current_segments:
                chunk_text = " ".join(s.text for s in current_segments)
                chunk_tokens = self.llm_service.count_tokens(chunk_text)
                if chunk_tokens + seg_tokens > self.max_chunk_size:
                    chunks.append(self._create_chunk(current_segments, chunk_idx, chunk_tokens))
                    chunk_idx += 1
                    current_segments = self._get_overlap(current_segments + [segment], chunk_overlap)
                    current_tokens = sum(self.llm_service.count_tokens(s.text) for s in current_segments)
                    continue

            current_segments.append(segment)
            current_tokens += seg_tokens

            if current_tokens >= chunk_size:
                chunk_text = " ".join(s.text for s in current_segments)
                chunk_tokens = self.llm_service.count_tokens(chunk_text)
                chunks.append(self._create_chunk(current_segments, chunk_idx, chunk_tokens))
                chunk_idx += 1
                current_segments = self._get_overlap(current_segments, chunk_overlap)
                current_tokens = sum(self.llm_service.count_tokens(s.text) for s in current_segments)

        if current_segments:
            chunk_text = " ".join(s.text for s in current_segments)
            chunk_tokens = self.llm_service.count_tokens(chunk_text)
            chunks.append(self._create_chunk(current_segments, chunk_idx, chunk_tokens))

        return chunks

    def _create_chunk(self, segments: list[TranscriptSegment], idx: int, tokens: int) -> Chunk:
        content = " ".join(s.text for s in segments)
        return Chunk(content, segments[0].start, segments[-1].end, idx, tokens)

    def _get_overlap(self, segments: list[TranscriptSegment], target: int) -> list[TranscriptSegment]:
        overlap = []
        overlap_tokens = 0
        for seg in reversed(segments):
            seg_tokens = self.llm_service.count_tokens(seg.text)
            if overlap_tokens + seg_tokens <= target:
                overlap.insert(0, seg)
                overlap_tokens += seg_tokens
            else:
                break
        return overlap
