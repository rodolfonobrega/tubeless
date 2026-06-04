"""YouTube service for searching and fetching video metadata using yt-dlp."""

import asyncio
import logging
from typing import Any

import yt_dlp

logger = logging.getLogger(__name__)

import os as _os
_browser = _os.environ.get("YTDLP_COOKIES_BROWSER", "chrome")
_cookies_file = _os.environ.get("YTDLP_COOKIES_FILE")

if _cookies_file:
    # Use specified cookies file (e.g. cookies.txt)
    YDL_OPTS: dict = {"quiet": True, "no_warnings": True, "extract_flat": True, "cookiefile": _cookies_file}
elif _browser:
    # Fallback to local browser cookies
    YDL_OPTS: dict = {"quiet": True, "no_warnings": True, "extract_flat": True, "cookiesfrombrowser": (_browser,)}
else:
    # Run without cookies if both are unset
    YDL_OPTS: dict = {"quiet": True, "no_warnings": True, "extract_flat": True}


class YouTubeSearchResult:
    def __init__(
        self,
        video_id: str,
        title: str,
        description: str,
        thumbnail_url: str,
        channel_title: str,
        channel_id: str,
        duration: int | None = None,
        published_at: str | None = None,
        view_count: int | None = None,
    ) -> None:
        self.video_id = video_id
        self.title = title
        self.description = description
        self.thumbnail_url = thumbnail_url
        self.channel_title = channel_title
        self.channel_id = channel_id
        self.duration = duration
        self.published_at = published_at
        self.view_count = view_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "video_id": self.video_id,
            "title": self.title,
            "description": self.description,
            "thumbnail_url": self.thumbnail_url,
            "channel_title": self.channel_title,
            "channel_id": self.channel_id,
            "duration": self.duration,
            "published_at": self.published_at,
            "view_count": self.view_count,
        }


class YouTubeService:
    """Service for searching YouTube and fetching video metadata using yt-dlp."""

    async def search(
        self,
        query: str,
        max_results: int = 10,
        duration_filter: str | None = None,
    ) -> list[YouTubeSearchResult]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._search_sync, query, max_results)

    def _search_sync(self, query: str, max_results: int) -> list[YouTubeSearchResult]:
        opts = {**YDL_OPTS, "extract_flat": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)

        results = []
        for entry in info.get("entries", []):
            if not entry:
                continue
            results.append(
                YouTubeSearchResult(
                    video_id=entry.get("id", ""),
                    title=entry.get("title", ""),
                    description=entry.get("description") or "",
                    thumbnail_url=self._best_thumbnail(entry.get("thumbnails") or []),
                    channel_title=entry.get("uploader") or entry.get("channel") or "",
                    channel_id=entry.get("channel_id") or "",
                    duration=entry.get("duration"),
                    published_at=entry.get("upload_date"),
                    view_count=entry.get("view_count"),
                )
            )
        return results

    async def get_video_details(self, video_id: str) -> dict[str, Any] | None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_details_sync, video_id)

    def _get_details_sync(self, video_id: str) -> dict[str, Any] | None:
        url = f"https://www.youtube.com/watch?v={video_id}"
        opts = {**YDL_OPTS, "extract_flat": False}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            return {
                "video_id": video_id,
                "title": info.get("title", ""),
                "description": info.get("description") or "",
                "thumbnail_url": self._best_thumbnail(info.get("thumbnails") or []),
                "channel_title": info.get("uploader") or info.get("channel") or "",
                "channel_id": info.get("channel_id") or "",
                "published_at": info.get("upload_date"),
                "duration": info.get("duration"),
                "view_count": info.get("view_count"),
            }
        except Exception as e:
            logger.error(f"Video details error for {video_id}: {e}")
            return None

    def _best_thumbnail(self, thumbnails: list[dict[str, Any]]) -> str:
        if not thumbnails:
            return ""
        # yt-dlp retorna thumbnails ordenadas da menor para a maior
        return thumbnails[-1].get("url", "")
