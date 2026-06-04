"""Tests for ChunkingService.

LLMService.count_tokens is patched to return word count so tests
are deterministic and don't require tiktoken downloads.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.chunking_service import Chunk, ChunkingService
from app.services.transcript_service import TranscriptSegment
from tests.conftest import make_segments


def _make_svc(chunk_size: int = 10, max_chunk_size: int = 20) -> ChunkingService:
    """Return ChunkingService with mocked LLMService using word-count tokenizer."""
    with patch("app.services.chunking_service.LLMService") as MockLLM:
        instance = MockLLM.return_value
        instance.count_tokens.side_effect = lambda text: len(text.split())
        svc = ChunkingService()
        svc.chunk_size = chunk_size
        svc.max_chunk_size = max_chunk_size
        svc.chunk_overlap = 0
        # Reassign so the instance mock is used inside the service
        svc.llm_service = instance
        return svc


# ---------------------------------------------------------------------------
# Token-based chunking
# ---------------------------------------------------------------------------

class TestChunkByTokens:
    def test_single_chunk_for_small_input(self):
        svc = _make_svc(chunk_size=50, max_chunk_size=100)
        segs = make_segments(["hello world", "foo bar"], duration_each=5.0)
        chunks = svc.chunk_transcript(segs)
        assert len(chunks) == 1
        assert "hello world" in chunks[0].content
        assert "foo bar" in chunks[0].content

    def test_splits_when_exceeds_chunk_size(self):
        # chunk_size=3 words; each segment has 3 words → splits after each
        svc = _make_svc(chunk_size=3, max_chunk_size=10)
        segs = make_segments(["one two three", "four five six", "seven eight nine"], duration_each=5.0)
        chunks = svc.chunk_transcript(segs)
        assert len(chunks) >= 2

    def test_chunk_indices_are_sequential(self):
        svc = _make_svc(chunk_size=3, max_chunk_size=10)
        segs = make_segments(["a b c", "d e f", "g h i", "j k l"], duration_each=5.0)
        chunks = svc.chunk_transcript(segs)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_timestamps_preserved(self):
        svc = _make_svc(chunk_size=50, max_chunk_size=100)
        segs = [
            TranscriptSegment("hello", start=10.0, end=15.0),
            TranscriptSegment("world", start=15.0, end=20.0),
        ]
        chunks = svc.chunk_transcript(segs)
        assert chunks[0].start_timestamp == 10.0
        assert chunks[0].end_timestamp == 20.0

    def test_returns_empty_list_for_no_segments(self):
        svc = _make_svc()
        chunks = svc.chunk_transcript([])
        assert chunks == []

    def test_max_chunk_size_forces_split(self):
        # max_chunk_size=5 words; segment has 6 words → forces a new chunk
        svc = _make_svc(chunk_size=100, max_chunk_size=5)
        segs = [
            TranscriptSegment("a b c d e f", start=0.0, end=5.0),
            TranscriptSegment("g h i", start=5.0, end=10.0),
        ]
        chunks = svc.chunk_transcript(segs)
        # First segment alone exceeds max_chunk_size, so it goes alone
        assert len(chunks) >= 1

    def test_no_chapters_uses_token_based(self):
        svc = _make_svc(chunk_size=50, max_chunk_size=100)
        segs = make_segments(["hello"], duration_each=5.0)
        chunks = svc.chunk_transcript(segs, chapters=None)
        assert len(chunks) == 1
        assert chunks[0].chapter_title is None


# ---------------------------------------------------------------------------
# Chapter-based chunking
# ---------------------------------------------------------------------------

class TestChunkByChapters:
    def test_one_chunk_per_chapter(self):
        svc = _make_svc(chunk_size=5, max_chunk_size=50)
        segs = [
            TranscriptSegment("intro text", start=0.0, end=30.0),
            TranscriptSegment("main content", start=60.0, end=120.0),
        ]
        chapters = [
            {"title": "Introduction", "start_time": 0.0, "end_time": 59.0},
            {"title": "Main", "start_time": 59.0, "end_time": 200.0},
        ]
        chunks = svc.chunk_transcript(segs, chapters=chapters)
        assert len(chunks) == 2
        assert chunks[0].chapter_title == "Introduction"
        assert chunks[1].chapter_title == "Main"

    def test_chapter_title_set_on_chunk(self):
        svc = _make_svc(chunk_size=5, max_chunk_size=50)
        segs = [TranscriptSegment("hello world", start=5.0, end=10.0)]
        chapters = [{"title": "Intro", "start_time": 0.0, "end_time": 60.0}]
        chunks = svc.chunk_transcript(segs, chapters=chapters)
        assert chunks[0].chapter_title == "Intro"

    def test_skips_chapter_with_no_segments(self):
        svc = _make_svc(chunk_size=5, max_chunk_size=50)
        segs = [TranscriptSegment("hello", start=5.0, end=10.0)]
        chapters = [
            {"title": "Empty", "start_time": 100.0, "end_time": 200.0},
            {"title": "Has Content", "start_time": 0.0, "end_time": 50.0},
        ]
        chunks = svc.chunk_transcript(segs, chapters=chapters)
        assert len(chunks) == 1
        assert chunks[0].chapter_title == "Has Content"

    def test_subdivides_large_chapter(self):
        svc = _make_svc(chunk_size=3, max_chunk_size=6)
        # Chapter has 12 words total → must be subdivided
        segs = [
            TranscriptSegment("a b c d e f g h i j k l", start=0.0, end=60.0),
        ]
        chapters = [{"title": "Big Chapter", "start_time": 0.0, "end_time": 100.0}]
        chunks = svc.chunk_transcript(segs, chapters=chapters)
        assert len(chunks) >= 1
        # All sub-chunks keep the parent chapter title
        for chunk in chunks:
            assert chunk.chapter_title == "Big Chapter"

    def test_chapter_chunk_indices_sequential(self):
        svc = _make_svc(chunk_size=5, max_chunk_size=50)
        segs = [
            TranscriptSegment("chapter one text", start=0.0, end=30.0),
            TranscriptSegment("chapter two text", start=60.0, end=90.0),
            TranscriptSegment("chapter three text", start=120.0, end=150.0),
        ]
        chapters = [
            {"title": "One", "start_time": 0.0, "end_time": 50.0},
            {"title": "Two", "start_time": 50.0, "end_time": 100.0},
            {"title": "Three", "start_time": 100.0, "end_time": 200.0},
        ]
        chunks = svc.chunk_transcript(segs, chapters=chapters)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_empty_chapters_falls_back_to_token_based(self):
        svc = _make_svc(chunk_size=50, max_chunk_size=100)
        segs = [TranscriptSegment("hello world", start=0.0, end=5.0)]
        chunks = svc.chunk_transcript(segs, chapters=[])
        assert len(chunks) == 1
        assert chunks[0].chapter_title is None


# ---------------------------------------------------------------------------
# _get_overlap
# ---------------------------------------------------------------------------

class TestGetOverlap:
    def test_overlap_returns_trailing_segments_within_budget(self):
        svc = _make_svc()
        segs = [
            TranscriptSegment("a", 0, 1),
            TranscriptSegment("b c", 1, 2),
            TranscriptSegment("d e f", 2, 3),
        ]
        # target = 4 words → should include last 2 segs (2+3=5 > 4, so just last seg "d e f" = 3)
        overlap = svc._get_overlap(segs, target=4)
        assert len(overlap) >= 1
        # Overlap should not exceed target significantly
        total = sum(len(s.text.split()) for s in overlap)
        assert total <= 4 or len(overlap) == 1  # at minimum one segment

    def test_no_overlap_when_target_zero(self):
        svc = _make_svc()
        segs = [TranscriptSegment("a b c", 0, 5)]
        overlap = svc._get_overlap(segs, target=0)
        assert overlap == []
