"""Comment service: fetches and batches YouTube comments via yt-dlp."""

import asyncio
import logging

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

_MIN_WORDS = 3
_BATCH_SIZE = 10


class CommentService:
    async def fetch_comments(self, video_id: str) -> list[str]:
        """Fetch top comments and return them as batched text chunks.

        Args:
            video_id: YouTube video ID (not URL)

        Returns:
            List of text chunks, each containing ~BATCH_SIZE comments.
        """
        url = f"https://www.youtube.com/watch?v={video_id}"
        max_comments = settings.max_comments

        def _run() -> list[dict]:
            import yt_dlp

            opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
                "skip_download": True,
                "getcomments": True,
                "extractor_args": {"youtube": {"max_comments": [str(max_comments)]}},
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get("comments") or []

        try:
            raw_comments = await asyncio.get_event_loop().run_in_executor(None, _run)
        except Exception as e:
            logger.warning(f"Comment fetch error for {video_id}: {e}")
            return []

        # Filter noise and sort by likes
        filtered = [
            c for c in raw_comments
            if c.get("text") and len(c["text"].split()) >= _MIN_WORDS
        ]
        filtered.sort(key=lambda c: c.get("like_count") or 0, reverse=True)
        texts = [c["text"].strip() for c in filtered[:max_comments]]

        # Batch into chunks of _BATCH_SIZE comments each
        batches = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            batches.append("\n\n".join(f"- {t}" for t in batch))

        return batches
