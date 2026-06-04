"""Tests for QueryExpansionService."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.query_expansion_service import QueryExpansionService
from tests.conftest import make_llm_response


@pytest.fixture
def svc():
    with patch("app.services.query_expansion_service.LLMService"):
        service = QueryExpansionService()
        service.llm = MagicMock()
        return service


class TestQueryExpansion:
    @pytest.mark.asyncio
    async def test_returns_list_of_strings(self, svc):
        terms = ["como aprender inglês", "english learning tips", "learn english fast"]
        svc.llm.completion = AsyncMock(return_value=make_llm_response(json.dumps(terms)))

        result = await svc.expand("como aprender inglês")
        assert result == terms

    @pytest.mark.asyncio
    async def test_strips_markdown_json_code_block(self, svc):
        terms = ["term one here", "term two here"]
        content = f"```json\n{json.dumps(terms)}\n```"
        svc.llm.completion = AsyncMock(return_value=make_llm_response(content))

        result = await svc.expand("query")
        assert result == terms

    @pytest.mark.asyncio
    async def test_strips_generic_code_block(self, svc):
        terms = ["generic term one", "generic term two"]
        content = f"```\n{json.dumps(terms)}\n```"
        svc.llm.completion = AsyncMock(return_value=make_llm_response(content))

        result = await svc.expand("query")
        assert result == terms

    @pytest.mark.asyncio
    async def test_fallback_on_llm_error(self, svc):
        svc.llm.completion = AsyncMock(side_effect=Exception("network error"))

        result = await svc.expand("original query")
        assert result == ["original query"]

    @pytest.mark.asyncio
    async def test_fallback_on_invalid_json(self, svc):
        svc.llm.completion = AsyncMock(return_value=make_llm_response("not json at all"))

        result = await svc.expand("original query")
        assert result == ["original query"]

    @pytest.mark.asyncio
    async def test_fallback_when_non_string_items_in_list(self, svc):
        # LLM returns a list that's not all strings
        content = json.dumps(["valid string", 42, None])
        svc.llm.completion = AsyncMock(return_value=make_llm_response(content))

        result = await svc.expand("original query")
        assert result == ["original query"]

    @pytest.mark.asyncio
    async def test_correct_number_of_terms_requested(self, svc):
        captured = {}

        async def fake_completion(messages, **kwargs):
            captured["prompt"] = messages[0]["content"]
            return make_llm_response(json.dumps(["t1", "t2", "t3", "t4", "t5", "t6"]))

        svc.llm.completion = fake_completion

        await svc.expand("query", terms_per_language=3)
        assert "3" in captured["prompt"]

    @pytest.mark.asyncio
    async def test_query_included_in_prompt(self, svc):
        captured = {}

        async def fake_completion(messages, **kwargs):
            captured["prompt"] = messages[0]["content"]
            return make_llm_response(json.dumps(["term a b c"]))

        svc.llm.completion = fake_completion

        await svc.expand("melhores SUV 2026")
        assert "melhores SUV 2026" in captured["prompt"]

    @pytest.mark.asyncio
    async def test_returns_list_not_single_string(self, svc):
        svc.llm.completion = AsyncMock(return_value=make_llm_response(json.dumps(["a b c", "d e f"])))

        result = await svc.expand("query")
        assert isinstance(result, list)
        assert all(isinstance(t, str) for t in result)
