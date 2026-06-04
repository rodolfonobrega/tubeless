"""Tests for LLMService — mocks litellm to avoid real API calls."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm_service import LLMService
from tests.conftest import make_llm_response


def _make_svc(model: str = "gpt-4o-mini") -> LLMService:
    with patch("app.services.llm_service.litellm"):
        return LLMService(model=model)


# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------

class TestModelSelection:
    def test_uses_provided_model(self):
        svc = _make_svc("groq/llama-3.3-70b-versatile")
        assert svc.model == "groq/llama-3.3-70b-versatile"

    def test_uses_default_model_when_none(self):
        with patch("app.services.llm_service.litellm"):
            svc = LLMService()
        # default_model from settings
        assert svc.model is not None
        assert isinstance(svc.model, str)


# ---------------------------------------------------------------------------
# completion
# ---------------------------------------------------------------------------

class TestCompletion:
    @pytest.mark.asyncio
    async def test_passes_model_to_litellm(self):
        svc = _make_svc("gpt-4o")
        mock_resp = make_llm_response("answer")

        with patch("app.services.llm_service.acompletion", AsyncMock(return_value=mock_resp)) as mock_ac:
            await svc.completion(messages=[{"role": "user", "content": "hello"}])
            call_kwargs = mock_ac.call_args.kwargs
            assert call_kwargs["model"] == "gpt-4o"

    @pytest.mark.asyncio
    async def test_passes_messages(self):
        svc = _make_svc()
        messages = [{"role": "user", "content": "test message"}]
        mock_resp = make_llm_response("ok")

        with patch("app.services.llm_service.acompletion", AsyncMock(return_value=mock_resp)) as mock_ac:
            await svc.completion(messages=messages)
            assert mock_ac.call_args.kwargs["messages"] == messages

    @pytest.mark.asyncio
    async def test_injects_reasoning_effort_when_set(self):
        svc = _make_svc()
        mock_resp = make_llm_response("ok")

        with patch("app.services.llm_service.acompletion", AsyncMock(return_value=mock_resp)) as mock_ac, \
             patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.reasoning_effort = "high"
            mock_settings.temperature = 0.7
            mock_settings.max_tokens = 4096
            await svc.completion(messages=[{"role": "user", "content": "x"}])
            call_kwargs = mock_ac.call_args.kwargs
            assert call_kwargs.get("reasoning_effort") == "high"

    @pytest.mark.asyncio
    async def test_skips_reasoning_effort_when_not_set(self):
        svc = _make_svc()
        mock_resp = make_llm_response("ok")

        with patch("app.services.llm_service.acompletion", AsyncMock(return_value=mock_resp)) as mock_ac, \
             patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.reasoning_effort = None
            mock_settings.temperature = 0.7
            mock_settings.max_tokens = 4096
            await svc.completion(messages=[{"role": "user", "content": "x"}])
            call_kwargs = mock_ac.call_args.kwargs
            assert "reasoning_effort" not in call_kwargs

    @pytest.mark.asyncio
    async def test_raises_on_litellm_error(self):
        svc = _make_svc()
        with patch("app.services.llm_service.acompletion", AsyncMock(side_effect=Exception("API error"))):
            with pytest.raises(Exception, match="API error"):
                await svc.completion(messages=[{"role": "user", "content": "x"}])

    @pytest.mark.asyncio
    async def test_kwargs_override_defaults(self):
        svc = _make_svc()
        mock_resp = make_llm_response("ok")

        with patch("app.services.llm_service.acompletion", AsyncMock(return_value=mock_resp)) as mock_ac:
            await svc.completion(
                messages=[{"role": "user", "content": "x"}],
                temperature=0.0,
                max_tokens=100,
            )
            call_kwargs = mock_ac.call_args.kwargs
            assert call_kwargs["temperature"] == 0.0
            assert call_kwargs["max_tokens"] == 100


# ---------------------------------------------------------------------------
# generate_embedding
# ---------------------------------------------------------------------------

class TestGenerateEmbedding:
    @pytest.mark.asyncio
    async def test_returns_embedding_vector(self):
        svc = _make_svc()
        vector = [0.1] * 1536
        mock_resp = MagicMock()
        mock_resp.data = [{"embedding": vector}]

        with patch("app.services.llm_service.aembedding", AsyncMock(return_value=mock_resp)):
            result = await svc.generate_embedding("hello world")
        assert result == vector

    @pytest.mark.asyncio
    async def test_uses_default_embedding_model(self):
        svc = _make_svc()
        mock_resp = MagicMock()
        mock_resp.data = [{"embedding": [0.1]}]

        with patch("app.services.llm_service.aembedding", AsyncMock(return_value=mock_resp)) as mock_ae, \
             patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.default_embedding_model = "text-embedding-3-small"
            await svc.generate_embedding("text")
            assert mock_ae.call_args.kwargs["model"] == "text-embedding-3-small"

    @pytest.mark.asyncio
    async def test_uses_override_model(self):
        svc = _make_svc()
        mock_resp = MagicMock()
        mock_resp.data = [{"embedding": [0.2]}]

        with patch("app.services.llm_service.aembedding", AsyncMock(return_value=mock_resp)) as mock_ae:
            await svc.generate_embedding("text", model="text-embedding-ada-002")
            assert mock_ae.call_args.kwargs["model"] == "text-embedding-ada-002"


# ---------------------------------------------------------------------------
# count_tokens
# ---------------------------------------------------------------------------

class TestCountTokens:
    def test_returns_integer(self):
        svc = _make_svc()
        count = svc.count_tokens("hello world foo bar")
        assert isinstance(count, int)
        assert count > 0

    def test_longer_text_has_more_tokens(self):
        svc = _make_svc()
        short = svc.count_tokens("hi")
        long = svc.count_tokens("this is a much longer sentence with many more words in it")
        assert long > short

    def test_empty_string_returns_zero_or_small(self):
        svc = _make_svc()
        count = svc.count_tokens("")
        assert count == 0

    def test_fallback_on_tiktoken_error(self):
        svc = _make_svc()
        with patch("tiktoken.get_encoding", side_effect=Exception("no tiktoken")):
            count = svc.count_tokens("hello world")
        # Fallback: len("hello world") // 4 = 2
        assert isinstance(count, int)
        assert count >= 0
