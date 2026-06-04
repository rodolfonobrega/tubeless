"""Tests for TranscriptService — pure methods only (no network calls)."""

import pytest

from app.services.transcript_service import TranscriptService


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
