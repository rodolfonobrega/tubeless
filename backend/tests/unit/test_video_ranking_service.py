"""Tests for VideoRankingService and _is_temporal_query."""

import json
import pytest
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.video_ranking_service import VideoRankingService, _is_temporal_query
from tests.conftest import make_llm_response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@contextmanager
def _mock_ranking_svc(response_content: str):
    """Create a VideoRankingService with mocked LLM returning given content."""
    with patch("app.services.video_ranking_service.LLMService") as MockLLM:
        instance = MockLLM.return_value
        instance.completion = AsyncMock(return_value=make_llm_response(response_content))
        yield VideoRankingService()


@contextmanager
def _mock_ranking_svc_error(exc: Exception):
    """VideoRankingService with LLM that raises."""
    with patch("app.services.video_ranking_service.LLMService") as MockLLM:
        instance = MockLLM.return_value
        instance.completion = AsyncMock(side_effect=exc)
        yield VideoRankingService()


def _make_videos(n: int) -> list[dict]:
    return [
        {
            "id": f"vid{i}",
            "title": f"Video {i}",
            "description": f"Description {i}",
            "published_at": "20260101",
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# _is_temporal_query (pure function)
# ---------------------------------------------------------------------------

class TestIsTemporalQuery:
    @pytest.mark.parametrize("query,expected", [
        ("melhores SUV 2026", True),
        ("melhor notebook 2025", True),
        ("melhores smartphones 2024", True),
        ("novo iPhone lançamento", True),
        ("novos modelos de carro", True),
        ("recente atualização python", True),
        ("latest python version", True),
        ("new macbook pro features", True),
        ("best SUVs 2026", True),
        ("melhores 2026 celulares", True),
        # Non-temporal
        ("como aprender inglês rápido", False),
        ("receita de bolo de chocolate", False),
        ("história do brasil", False),
        ("python tutorial completo", False),
        # Year 2023 should NOT match (pattern only captures 202[4-9] and 203x)
        ("melhores carros 2023", False),
        ("melhores carros 2022", False),
    ])
    def test_temporal_detection(self, query, expected):
        assert _is_temporal_query(query) == expected

    def test_case_insensitive_novo(self):
        assert _is_temporal_query("NOVO produto lançado") is True

    def test_case_insensitive_latest(self):
        assert _is_temporal_query("Latest Update") is True


# ---------------------------------------------------------------------------
# VideoRankingService.rank — with mocked LLM
# ---------------------------------------------------------------------------

class TestVideoRankingRank:
    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_input(self):
        with _mock_ranking_svc("[]") as svc:
            result = await svc.rank("query", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_marks_top_n_as_preselected(self):
        rankings = [
            {"index": 0, "score": 9, "reason": "best"},
            {"index": 1, "score": 8, "reason": "good"},
            {"index": 2, "score": 7, "reason": "ok"},
            {"index": 3, "score": 6, "reason": "meh"},
            {"index": 4, "score": 5, "reason": "barely"},
        ]
        with _mock_ranking_svc(json.dumps(rankings)) as svc:
            result = await svc.rank("query", _make_videos(5), pre_selected_count=3)

        preselected = [v for v in result if v["pre_selected"]]
        assert len(preselected) == 3

    @pytest.mark.asyncio
    async def test_filters_videos_below_score_threshold(self):
        rankings = [
            {"index": 0, "score": 8, "reason": "great"},
            {"index": 1, "score": 3, "reason": "poor"},
            {"index": 2, "score": 2, "reason": "worse"},
            {"index": 3, "score": 7, "reason": "good"},
        ]
        with _mock_ranking_svc(json.dumps(rankings)) as svc:
            result = await svc.rank("query", _make_videos(4), pre_selected_count=3)

        ids = [v["id"] for v in result]
        assert "vid1" not in ids
        assert "vid2" not in ids
        assert "vid0" in ids
        assert "vid3" in ids

    @pytest.mark.asyncio
    async def test_sorted_by_score_descending(self):
        rankings = [
            {"index": 0, "score": 5, "reason": "mid"},
            {"index": 1, "score": 9, "reason": "top"},
            {"index": 2, "score": 7, "reason": "good"},
        ]
        with _mock_ranking_svc(json.dumps(rankings)) as svc:
            result = await svc.rank("query", _make_videos(3), pre_selected_count=1)

        scores = [v["relevance_score"] for v in result]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_relevance_score_and_reason_set(self):
        rankings = [{"index": 0, "score": 8, "reason": "highly relevant"}]
        with _mock_ranking_svc(json.dumps(rankings)) as svc:
            result = await svc.rank("query", _make_videos(1), pre_selected_count=1)

        assert result[0]["relevance_score"] == 8
        assert result[0]["relevance_reason"] == "highly relevant"

    @pytest.mark.asyncio
    async def test_fallback_on_llm_error(self):
        with _mock_ranking_svc_error(Exception("LLM down")) as svc:
            result = await svc.rank("query", _make_videos(4), pre_selected_count=2)

        assert len(result) == 4
        preselected = [v for v in result if v["pre_selected"]]
        assert len(preselected) == 2

    @pytest.mark.asyncio
    async def test_fallback_on_invalid_json(self):
        with _mock_ranking_svc("not valid json {{{{") as svc:
            result = await svc.rank("query", _make_videos(2), pre_selected_count=1)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_temporal_query_adds_instruction_to_prompt(self):
        captured = {}

        with patch("app.services.video_ranking_service.LLMService") as MockLLM:
            async def fake_completion(messages, **kwargs):
                captured["content"] = messages[0]["content"]
                return make_llm_response(json.dumps([{"index": 0, "score": 8, "reason": "ok"}]))

            MockLLM.return_value.completion = fake_completion
            svc = VideoRankingService()
            await svc.rank("melhores SUV 2026", _make_videos(1), pre_selected_count=1)

        assert "time-sensitive" in captured["content"]

    @pytest.mark.asyncio
    async def test_non_temporal_query_no_time_instruction(self):
        captured = {}

        with patch("app.services.video_ranking_service.LLMService") as MockLLM:
            async def fake_completion(messages, **kwargs):
                captured["content"] = messages[0]["content"]
                return make_llm_response(json.dumps([{"index": 0, "score": 8, "reason": "ok"}]))

            MockLLM.return_value.completion = fake_completion
            svc = VideoRankingService()
            await svc.rank("como aprender inglês", _make_videos(1), pre_selected_count=1)

        assert "time-sensitive" not in captured["content"]

    @pytest.mark.asyncio
    async def test_published_at_included_in_prompt(self):
        captured = {}
        videos = [{"id": "v1", "title": "Video", "description": "desc", "published_at": "20260101"}]

        with patch("app.services.video_ranking_service.LLMService") as MockLLM:
            async def fake_completion(messages, **kwargs):
                captured["content"] = messages[0]["content"]
                return make_llm_response(json.dumps([{"index": 0, "score": 8, "reason": "ok"}]))

            MockLLM.return_value.completion = fake_completion
            svc = VideoRankingService()
            await svc.rank("query", videos, pre_selected_count=1)

        assert "20260101" in captured["content"]
