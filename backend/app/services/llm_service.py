"""LLM service using LiteLLM for provider-agnostic AI completions."""

import logging
from collections.abc import AsyncGenerator, Iterable
from typing import Any

import litellm
from litellm import acompletion, aembedding

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def _eff(key: str, default: Any) -> Any:
    """Read effective setting (DB override) if cached, else env default."""
    try:
        from app.core.effective_settings import _cache
        if _cache is not None and key in _cache:
            return _cache[key]
    except Exception:
        pass
    return default


class LLMService:
    """Service for LLM operations using LiteLLM."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
    ) -> None:
        """Initialize the LLM service.

        Args:
            model: The model to use. Defaults to settings.default_model.
            api_key: Optional API key override.
            api_base: Optional API base URL override.
        """
        self.model = model or _eff("default_model", settings.default_model)
        self.api_key = api_key
        self.api_base = api_base

        # Configure litellm
        litellm.set_verbose = settings.debug
        litellm.drop_params = True  # Drop unsupported params for specific providers

    async def completion(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate a chat completion.

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            stream: Whether to stream the response.
            **kwargs: Additional parameters for the LLM.

        Returns:
            The completion response.
        """
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else _eff("temperature", settings.temperature),
            "max_tokens": max_tokens if max_tokens is not None else _eff("max_tokens", settings.max_tokens),
            "stream": stream,
            **kwargs,
        }

        if self.api_key:
            params["api_key"] = self.api_key
        if self.api_base:
            params["api_base"] = self.api_base
        eff_reasoning = _eff("reasoning_effort", settings.reasoning_effort)
        if eff_reasoning and "reasoning_effort" not in kwargs:
            params["reasoning_effort"] = eff_reasoning

        params.setdefault("timeout", 30)
        try:
            response = await acompletion(**params)
            return response  # type: ignore[no-any-return]
        except Exception as e:
            logger.error(f"LLM completion error: {e}")
            raise

    async def stream_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion.

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters for the LLM.

        Yields:
            Chunks of the generated text.
        """
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else _eff("temperature", settings.temperature),
            "max_tokens": max_tokens if max_tokens is not None else _eff("max_tokens", settings.max_tokens),
            "stream": True,
            **kwargs,
        }

        if self.api_key:
            params["api_key"] = self.api_key
        if self.api_base:
            params["api_base"] = self.api_base
        eff_reasoning = _eff("reasoning_effort", settings.reasoning_effort)
        if eff_reasoning and "reasoning_effort" not in kwargs:
            params["reasoning_effort"] = eff_reasoning

        params.setdefault("timeout", 30)
        try:
            response = await acompletion(**params)
            async for chunk in response:  # type: ignore[attr-defined]
                if chunk.choices:
                    delta = chunk.choices[0].delta.get("content", "")
                    if delta:
                        yield delta
        except Exception as e:
            logger.error(f"LLM streaming error: {e}")
            raise

    async def generate_embedding(
        self,
        text: str,
        model: str | None = None,
    ) -> list[float]:
        """Generate an embedding for the given text.

        Args:
            text: The text to embed.
            model: The embedding model to use. Defaults to settings.default_embedding_model.

        Returns:
            The embedding vector as a list of floats.
        """
        embedding_model = model or _eff("default_embedding_model", settings.default_embedding_model)

        params = {
            "model": embedding_model,
            "input": text,
        }

        if self.api_key:
            params["api_key"] = self.api_key
        if self.api_base:
            params["api_base"] = self.api_base

        params.setdefault("timeout", 30)
        try:
            response = await aembedding(**params)
            return response.data[0]["embedding"]  # type: ignore[index,no-any-return]
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            raise

    async def generate_embeddings_batch(
        self,
        texts: Iterable[str],
        model: str | None = None,
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: Iterable of texts to embed.
            model: The embedding model to use.

        Returns:
            List of embedding vectors.
        """
        embedding_model = model or _eff("default_embedding_model", settings.default_embedding_model)
        text_list = list(texts)

        if not text_list:
            return []

        params = {
            "model": embedding_model,
            "input": text_list,
        }

        if self.api_key:
            params["api_key"] = self.api_key
        if self.api_base:
            params["api_base"] = self.api_base

        try:
            response = await aembedding(**params)
            return [item["embedding"] for item in response.data]  # type: ignore[index,no-any-return]
        except Exception as e:
            logger.error(f"Batch embedding generation error: {e}")
            raise

    def count_tokens(self, text: str, model: str | None = None) -> int:
        """Count the number of tokens in a text.

        Args:
            text: The text to count tokens for.
            model: The model to use for tokenization.

        Returns:
            The number of tokens.
        """
        try:
            import tiktoken

            # Get encoding for the model
            encoding_name = "cl100k_base"  # Default for GPT-4 and GPT-3.5-turbo
            if model:
                if "gpt-4" in model:
                    encoding_name = "cl100k_base"
                elif "gpt-3.5" in model:
                    encoding_name = "cl100k_base"

            encoding = tiktoken.get_encoding(encoding_name)
            return len(encoding.encode(text))
        except Exception as e:
            logger.warning(f"Token counting error, using fallback: {e}")
            # Fallback: roughly 4 characters per token
            return len(text) // 4
