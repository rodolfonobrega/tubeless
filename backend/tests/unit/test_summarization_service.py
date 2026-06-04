"""Tests for SummarizationService map-reduce pipeline."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.summarization_service import (
    SummarizationService,
    VideoSummaryResult,
    ConsolidatedSummaryResult,
)
from app.services.chunking_service import Chunk
from tests.conftest import make_llm_response


def _make_chunk(text: str, idx: int = 0) -> Chunk:
    return Chunk(content=text, start_timestamp=0.0, end_timestamp=10.0, chunk_index=idx, token_count=10)


def _make_svc() -> SummarizationService:
    with patch("app.services.summarization_service.LLMService"):
        svc = SummarizationService()
        svc.llm_service = MagicMock()
        return svc


# ---------------------------------------------------------------------------
# summarize_chunks
# ---------------------------------------------------------------------------

class TestSummarizeChunks:
    @pytest.mark.asyncio
    async def test_raises_on_empty_chunks(self):
        svc = _make_svc()
        with pytest.raises(ValueError, match="No chunks"):
            await svc.summarize_chunks([])

    @pytest.mark.asyncio
    async def test_returns_video_summary_result(self):
        svc = _make_svc()
        map_response = make_llm_response("Chunk summary here.")
        reduce_json = json.dumps({
            "summary_text": "Full summary.",
            "key_points": [{"point": "Key point 1", "timestamp": "0:10"}],
            "topics": ["topic A", "topic B"],
        })
        reduce_response = make_llm_response(reduce_json)
        svc.llm_service.completion = AsyncMock(side_effect=[map_response, reduce_response])

        result = await svc.summarize_chunks([_make_chunk("Hello world")])
        assert isinstance(result, VideoSummaryResult)
        assert result.summary_text == "Full summary."
        assert result.key_points == [{"point": "Key point 1", "timestamp": "0:10"}]
        assert result.topics == ["topic A", "topic B"]

    @pytest.mark.asyncio
    async def test_map_calls_llm_once_per_chunk(self):
        svc = _make_svc()
        chunk_count = 3
        chunks = [_make_chunk(f"chunk {i}", i) for i in range(chunk_count)]

        map_responses = [make_llm_response(f"summary {i}") for i in range(chunk_count)]
        reduce_json = json.dumps({"summary_text": "done", "key_points": [], "topics": []})
        reduce_response = make_llm_response(reduce_json)

        call_responses = map_responses + [reduce_response]
        svc.llm_service.completion = AsyncMock(side_effect=call_responses)

        await svc.summarize_chunks(chunks)
        assert svc.llm_service.completion.call_count == chunk_count + 1  # N map + 1 reduce

    @pytest.mark.asyncio
    async def test_fallback_on_json_decode_error(self):
        svc = _make_svc()
        map_response = make_llm_response("Chunk summary.")
        reduce_response = make_llm_response("This is plain text, not JSON.")
        svc.llm_service.completion = AsyncMock(side_effect=[map_response, reduce_response])

        result = await svc.summarize_chunks([_make_chunk("text")])
        assert isinstance(result, VideoSummaryResult)
        assert result.summary_text == "This is plain text, not JSON."
        assert result.key_points == []
        assert result.topics == []

    @pytest.mark.asyncio
    async def test_strips_markdown_json_blocks(self):
        svc = _make_svc()
        map_response = make_llm_response("summary")
        json_data = {"summary_text": "Stripped summary.", "key_points": [], "topics": ["x"]}
        content = f"```json\n{json.dumps(json_data)}\n```"
        reduce_response = make_llm_response(content)
        svc.llm_service.completion = AsyncMock(side_effect=[map_response, reduce_response])

        result = await svc.summarize_chunks([_make_chunk("text")])
        assert result.summary_text == "Stripped summary."
        assert result.topics == ["x"]

    @pytest.mark.asyncio
    async def test_map_error_adds_placeholder(self):
        svc = _make_svc()
        error_response = Exception("LLM error")
        reduce_json = json.dumps({"summary_text": "done", "key_points": [], "topics": []})
        reduce_response = make_llm_response(reduce_json)

        svc.llm_service.completion = AsyncMock(side_effect=[error_response, reduce_response])

        # Should not raise — map error is caught, reduce gets placeholder
        result = await svc.summarize_chunks([_make_chunk("text")])
        assert isinstance(result, VideoSummaryResult)


# ---------------------------------------------------------------------------
# consolidate_video_summaries
# ---------------------------------------------------------------------------

class TestConsolidateVideoSummaries:
    @pytest.mark.asyncio
    async def test_raises_on_empty_summaries(self):
        svc = _make_svc()
        with pytest.raises(ValueError, match="No video summaries"):
            await svc.consolidate_video_summaries([], "query")

    @pytest.mark.asyncio
    async def test_returns_consolidated_result(self):
        svc = _make_svc()
        json_data = {
            "summary_text": "Cross-video synthesis.",
            "key_themes": [{"theme": "Learning", "sources": ["V1"], "description": "desc"}],
            "consensus_points": ["Both agree on X"],
            "differing_viewpoints": [],
            "contradictions": [],
        }
        svc.llm_service.completion = AsyncMock(return_value=make_llm_response(json.dumps(json_data)))

        summaries = [
            {"title": "Video 1", "summary_text": "Summary 1", "key_points": [], "topics": []},
            {"title": "Video 2", "summary_text": "Summary 2", "key_points": [], "topics": []},
        ]
        result = await svc.consolidate_video_summaries(summaries, "learning query")
        assert isinstance(result, ConsolidatedSummaryResult)
        assert result.summary_text == "Cross-video synthesis."
        assert result.key_themes[0]["theme"] == "Learning"
        assert result.consensus_points == ["Both agree on X"]

    @pytest.mark.asyncio
    async def test_contradictions_populated(self):
        svc = _make_svc()
        contradictions = [
            {
                "topic": "Method X",
                "claim_a": "Method X works",
                "source_a": "Video 1",
                "claim_b": "Method X does not work",
                "source_b": "Video 2",
            }
        ]
        json_data = {
            "summary_text": "Synthesis.",
            "key_themes": [],
            "consensus_points": [],
            "differing_viewpoints": [],
            "contradictions": contradictions,
        }
        svc.llm_service.completion = AsyncMock(return_value=make_llm_response(json.dumps(json_data)))

        summaries = [
            {"title": "V1", "summary_text": "s1", "key_points": [], "topics": []},
            {"title": "V2", "summary_text": "s2", "key_points": [], "topics": []},
        ]
        result = await svc.consolidate_video_summaries(summaries, "query")
        assert len(result.contradictions) == 1
        assert result.contradictions[0]["topic"] == "Method X"

    @pytest.mark.asyncio
    async def test_contradictions_default_empty_on_fallback(self):
        svc = _make_svc()
        svc.llm_service.completion = AsyncMock(return_value=make_llm_response("plain text response"))

        summaries = [{"title": "V1", "summary_text": "s1", "key_points": [], "topics": []}]
        result = await svc.consolidate_video_summaries(summaries, "query")
        assert result.contradictions == []

    @pytest.mark.asyncio
    async def test_query_included_in_prompt(self):
        svc = _make_svc()
        captured = {}

        async def fake_completion(messages, **kwargs):
            captured["prompt"] = messages[1]["content"]
            return make_llm_response(json.dumps({
                "summary_text": "ok", "key_themes": [], "consensus_points": [],
                "differing_viewpoints": [], "contradictions": [],
            }))

        svc.llm_service.completion = fake_completion

        summaries = [{"title": "V1", "summary_text": "s1", "key_points": [], "topics": []}]
        await svc.consolidate_video_summaries(summaries, "melhores SUV 2026")
        assert "melhores SUV 2026" in captured["prompt"]

    @pytest.mark.asyncio
    async def test_video_titles_in_prompt(self):
        svc = _make_svc()
        captured = {}

        async def fake_completion(messages, **kwargs):
            captured["prompt"] = messages[1]["content"]
            return make_llm_response(json.dumps({
                "summary_text": "ok", "key_themes": [], "consensus_points": [],
                "differing_viewpoints": [], "contradictions": [],
            }))

        svc.llm_service.completion = fake_completion

        summaries = [
            {"title": "Amazing SUV Review", "summary_text": "Great car", "key_points": [], "topics": []},
        ]
        await svc.consolidate_video_summaries(summaries, "query")
        assert "Amazing SUV Review" in captured["prompt"]
