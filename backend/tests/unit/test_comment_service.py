"""Tests for CommentService filter/batch logic with mocked yt-dlp."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.comment_service import CommentService, _MIN_WORDS, _BATCH_SIZE


def _make_comment(text: str, likes: int = 0) -> dict:
    return {"text": text, "like_count": likes}


@pytest.fixture
def svc():
    return CommentService()


def _patch_ydl(comments: list[dict]):
    """Context manager that patches yt-dlp to return given comments."""
    mock_info = {"comments": comments}

    class FakeYDL:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def extract_info(self, *a, **kw):
            return mock_info

    return patch("yt_dlp.YoutubeDL", return_value=FakeYDL())


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

class TestCommentFiltering:
    @pytest.mark.asyncio
    async def test_filters_out_short_comments(self, svc):
        comments = [
            _make_comment("yo", 100),           # 1 word — filtered
            _make_comment("ok nice", 50),        # 2 words — filtered (< _MIN_WORDS=3)
            _make_comment("this is a valid comment", 10),
        ]
        with _patch_ydl(comments):
            batches = await svc.fetch_comments("abc123")

        combined = "\n".join(batches)
        assert "- yo" not in combined
        assert "ok nice" not in combined
        assert "this is a valid comment" in combined

    @pytest.mark.asyncio
    async def test_min_words_boundary(self, svc):
        # Exactly _MIN_WORDS words should pass; one below should be filtered
        text_exact = " ".join([f"uniq{i}" for i in range(_MIN_WORDS)])
        text_below = " ".join([f"skip{i}" for i in range(_MIN_WORDS - 1)])
        comments = [_make_comment(text_exact, 1), _make_comment(text_below, 2)]
        with _patch_ydl(comments):
            batches = await svc.fetch_comments("abc123")
        combined = "\n".join(batches)
        assert text_exact in combined
        assert text_below not in combined

    @pytest.mark.asyncio
    async def test_filters_empty_text(self, svc):
        comments = [_make_comment("", 999), _make_comment("valid comment here", 1)]
        with _patch_ydl(comments):
            batches = await svc.fetch_comments("abc123")
        combined = "\n".join(batches)
        assert "valid comment here" in combined


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------

class TestCommentSorting:
    @pytest.mark.asyncio
    async def test_sorts_by_likes_descending(self, svc):
        comments = [
            _make_comment("low likes comment here", 5),
            _make_comment("highest likes comment first", 1000),
            _make_comment("medium likes comment text", 50),
        ]
        with _patch_ydl(comments):
            batches = await svc.fetch_comments("abc123")

        first_batch = batches[0]
        # Highest-liked comment should appear before lower-liked ones
        pos_high = first_batch.find("highest likes")
        pos_med = first_batch.find("medium likes")
        assert pos_high < pos_med

    @pytest.mark.asyncio
    async def test_handles_missing_like_count(self, svc):
        comments = [
            {"text": "no like count here folks", "like_count": None},
            {"text": "another comment no likes", "like_count": None},
        ]
        with _patch_ydl(comments):
            batches = await svc.fetch_comments("abc123")
        assert len(batches) >= 1


# ---------------------------------------------------------------------------
# Batching
# ---------------------------------------------------------------------------

class TestCommentBatching:
    @pytest.mark.asyncio
    async def test_batches_into_groups_of_batch_size(self, svc):
        count = _BATCH_SIZE * 2 + 3
        comments = [_make_comment(f"comment number {i} here", i) for i in range(count)]
        with _patch_ydl(comments):
            batches = await svc.fetch_comments("abc123")
        assert len(batches) == 3  # 10 + 10 + 3

    @pytest.mark.asyncio
    async def test_single_batch_for_few_comments(self, svc):
        comments = [_make_comment(f"comment {i} here text", i) for i in range(5)]
        with _patch_ydl(comments):
            batches = await svc.fetch_comments("abc123")
        assert len(batches) == 1

    @pytest.mark.asyncio
    async def test_each_comment_prefixed_with_dash(self, svc):
        comments = [_make_comment("great video thanks so much", 10)]
        with _patch_ydl(comments):
            batches = await svc.fetch_comments("abc123")
        assert batches[0].startswith("- ")

    @pytest.mark.asyncio
    async def test_comments_separated_by_double_newline(self, svc):
        comments = [
            _make_comment("first comment is great", 2),
            _make_comment("second comment also great", 1),
        ]
        with _patch_ydl(comments):
            batches = await svc.fetch_comments("abc123")
        assert "\n\n" in batches[0]


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestCommentErrorHandling:
    @pytest.mark.asyncio
    async def test_returns_empty_list_on_yt_dlp_error(self, svc):
        with patch("yt_dlp.YoutubeDL", side_effect=Exception("network error")):
            batches = await svc.fetch_comments("abc123")
        assert batches == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_comments(self, svc):
        with _patch_ydl([]):
            batches = await svc.fetch_comments("abc123")
        assert batches == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_comments_filtered(self, svc):
        comments = [_make_comment("ok", 999), _make_comment("hi", 500)]
        with _patch_ydl(comments):
            batches = await svc.fetch_comments("abc123")
        assert batches == []


# ---------------------------------------------------------------------------
# URL construction
# ---------------------------------------------------------------------------

class TestUrlConstruction:
    @pytest.mark.asyncio
    async def test_uses_correct_youtube_url(self, svc):
        captured_url = {}

        def fake_ydl_factory(*args, **kwargs):
            class FakeYDL:
                def __enter__(self):
                    return self
                def __exit__(self, *a):
                    pass
                def extract_info(self, url, **kw):
                    captured_url["url"] = url
                    return {"comments": []}
            return FakeYDL()

        with patch("yt_dlp.YoutubeDL", side_effect=fake_ydl_factory):
            await svc.fetch_comments("dQw4w9WgXcQ")

        assert captured_url["url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
