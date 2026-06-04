"""Cross-Encoder reranking service using FlashRank (local, fast)."""

from typing import Any

from app.core.config import get_settings

settings = get_settings()


class RerankingService:
    """Service for cross-encoder reranking of retrieval results."""

    def __init__(self) -> None:
        # FlashRank uses a default "ms-marco-MiniLM-L-12-v2" model (~40MB)
        # It runs entirely locally with no API calls
        try:
            from flashrank import Ranker
            self._ranker: Any | None = Ranker()
        except Exception:
            self._ranker = None

    def rerank(
        self,
        query: str,
        passages: list[dict[str, Any]],
        top_n: int = 10,
    ) -> list[dict[str, Any]]:
        """Rerank passages using cross-encoder.

        Args:
            query: The search query.
            passages: List of passage dicts with at least "id" and "text" keys.
            top_n: Number of top results to return.

        Returns:
            Reranked passages with "score" key added.
        """
        if not self._ranker:
            # FlashRank not available — return top N by original order
            return passages[:top_n]

        if not passages:
            return []

        try:
            from flashrank import RerankRequest

            req = RerankRequest(
                query=query,
                passages=passages,
            )
            results = self._ranker.rerank(req)
            # Results are already sorted by score descending
            return results[:top_n]
        except Exception:
            # Fallback gracefully
            return passages[:top_n]
