"""Cross-Encoder reranking service using FlashRank (local, fast)."""

import logging
import threading
from typing import Any

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class RerankingService:
    """Service for cross-encoder reranking of retrieval results."""

    _ranker: Any | None = None
    _loading: bool = False
    _lock = threading.Lock()

    @classmethod
    def initialize(cls) -> None:
        """Initialize the FlashRank Ranker model.

        This method is thread-safe and loads the model once.
        """
        with cls._lock:
            if cls._ranker is not None or cls._loading:
                return
            cls._loading = True

        try:
            logger.info("Initializing FlashRank reranker (ms-marco-MiniLM-L-12-v2)...")
            from flashrank import Ranker
            ranker = Ranker()
            with cls._lock:
                cls._ranker = ranker
                cls._loading = False
            logger.info("FlashRank reranker initialized successfully.")
        except Exception as e:
            with cls._lock:
                cls._loading = False
            logger.error(f"Failed to initialize FlashRank reranker: {e}")

    @classmethod
    def start_background_init(cls) -> None:
        """Start initialization in a background thread to avoid blocking server startup."""
        thread = threading.Thread(
            target=cls.initialize,
            name="FlashRankInit",
            daemon=True,
        )
        thread.start()

    def __init__(self) -> None:
        # If not preloaded and not currently loading, trigger lazy loading
        if self._ranker is None and not self._loading:
            self.initialize()

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
            If the model is not initialized yet, returns top_n items by original order.
        """
        ranker = self._ranker
        if not ranker:
            # Fallback gracefully if model is still loading or failed to load
            logger.warning("FlashRank model not loaded yet or unavailable. Falling back to default order.")
            return passages[:top_n]

        if not passages:
            return []

        try:
            from flashrank import RerankRequest

            req = RerankRequest(
                query=query,
                passages=passages,
            )
            results = ranker.rerank(req)
            # Results are already sorted by score descending
            return results[:top_n]
        except Exception as e:
            logger.error(f"Error during reranking execution: {e}")
            # Fallback gracefully
            return passages[:top_n]

