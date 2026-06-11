"""Tests for TranscriptService - pure methods only (no network calls)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.transcript_service import TranscriptService, TranscriptUnavailableError


@pytest.fixture
def svc():
    return TranscriptService()


# ---------------------------------------------------------------------------
# _parse_timestamp
# ---------------------------------------------------------------------------


class TestParseTimestamp:
    def test_minutes_seconds(self, svc):
        assert svc._parse_timestamp("00:00") == 0.0
        assert svc._parse_timestamp("01:30") == 90.0
        assert svc._parse_timestamp("10:05") == 605.0

    def test_hours_minutes_seconds(self, svc):
        assert svc._parse_timestamp("01:00:00") == 3600.0
        assert svc._parse_timestamp("02:15:30") == 8130.0

    def test_invalid_formats(self, svc):
        assert svc._parse_timestamp("invalid") == 0.0
        assert svc._parse_timestamp("") == 0.0


# ---------------------------------------------------------------------------
# _extract_video_id
# ---------------------------------------------------------------------------


class TestExtractVideoId:
    def test_extracts_id_from_standard_url(self, svc):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert svc._extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extracts_id_from_shared_url(self, svc):
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert svc._extract_video_id(url) == "dQw4w9WgXcQ"

    def test_returns_id_if_already_bare_id(self, svc):
        assert svc._extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"


# ---------------------------------------------------------------------------
# yt-dlp fallback / error aggregation
# ---------------------------------------------------------------------------


class TestYtDlpFallback:
    @pytest.mark.asyncio
    async def test_builds_supported_yt_dlp_command(self, svc):
        commands = []

        def fake_run(cmd, capture_output, text, timeout):
            commands.append(cmd)
            return SimpleNamespace(returncode=1, stdout="", stderr="subtitles are not available")

        class DummyLoop:
            async def run_in_executor(self, executor, func):
                return func()

        with patch("subprocess.run", side_effect=fake_run), patch(
            "app.services.transcript_service.asyncio.get_event_loop",
            return_value=DummyLoop(),
        ):
            with pytest.raises(TranscriptUnavailableError):
                await svc._fetch_yt_dlp("abc123", ["en"])

        assert commands
        assert all("--convert-subs" not in cmd for cmd in commands)
        assert any("--dump-json" in cmd for cmd in commands)

    @pytest.mark.asyncio
    async def test_fetch_transcript_reports_all_strategy_failures(self, svc):
        with patch.object(
            svc,
            "_fetch_youtube_transcript_api",
            AsyncMock(side_effect=TranscriptUnavailableError("api unavailable")),
        ), patch.object(
            svc,
            "_fetch_yt_dlp",
            AsyncMock(side_effect=Exception("yt-dlp error: Usage: yt-dlp")),
        ), patch.object(
            svc,
            "_fetch_playwright",
            AsyncMock(side_effect=TranscriptUnavailableError("playwright empty")),
        ):
            with pytest.raises(TranscriptUnavailableError) as exc:
                await svc.fetch_transcript("abc123", languages=["en"])

        message = str(exc.value)
        assert "youtube_transcript_api" in message
        assert "yt_dlp" in message
        assert "playwright" in message


# ---------------------------------------------------------------------------
# _fetch_youtube_transcript_api
# ---------------------------------------------------------------------------


class TestFetchYoutubeTranscriptApi:
    @pytest.mark.asyncio
    async def test_fetch_youtube_transcript_api_success(self, svc):
        from unittest.mock import MagicMock

        mock_fetched = MagicMock()
        mock_fetched.to_raw_data.return_value = [
            {"text": "Hello", "start": 0.0, "duration": 2.0}
        ]
        mock_fetched.language_code = "en"

        mock_api_instance = MagicMock()
        mock_api_instance.fetch.return_value = mock_fetched

        with patch("youtube_transcript_api.YouTubeTranscriptApi", return_value=mock_api_instance):
            raw_text, segments, detected_lang, _, _ = await svc._fetch_youtube_transcript_api("abc123", ["en"])

        assert raw_text == "Hello"
        assert len(segments) == 1
        assert segments[0].text == "Hello"
        assert segments[0].start == 0.0
        assert segments[0].end == 2.0
        assert detected_lang == "en"
