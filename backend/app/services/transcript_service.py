"""Transcript service with cascading fallback: youtube-transcript-api → yt-dlp → Playwright."""

import asyncio
import concurrent.futures
import hashlib
import logging
import os
import random
import re
from typing import Any

from app.core.config import get_settings
from app.core.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)

_STORAGE_STATE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "yt_browser_state.json"
)

# Thread executor for Playwright sync API — needs its own thread
_playwright_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=3, thread_name_prefix="playwright"
)

# Resource types and URL patterns to block
_BLOCK_TYPES = {"image", "font", "media", "other"}
_BLOCK_RE = re.compile(
    r"googlevideo\.com|ytimg\.com/vi/|\.jpg|\.png|\.webp|\.gif|\.woff|\.ttf|\.mp4|\.m4v"
)


def _route_handler(route: Any) -> None:
    if route.request.resource_type in _BLOCK_TYPES or _BLOCK_RE.search(route.request.url):
        route.abort()
    else:
        route.continue_()


class TranscriptSegment:
    """Represents a segment of transcript with timing."""

    def __init__(self, text: str, start: float, end: float) -> None:
        self.text = text
        self.start = start
        self.end = end

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "start": self.start, "end": self.end}


class TranscriptUnavailableError(Exception):
    """Raised when a video truly has no transcript (so we should NOT retry)."""

    pass


class TranscriptService:
    """Fetch transcripts via cascading fallback."""

    async def fetch_transcript(
        self, video_url: str, languages: list[str] | None = None
    ) -> tuple[str, list[TranscriptSegment], str | None, list[dict], dict]:
        """Fetch transcript with cascading fallback and smart retry.

        Returns: (raw_text, segments, language, chapters, metadata)
        """
        languages = languages or settings.subtitle_languages
        video_id = self._extract_video_id(video_url)

        # Try each strategy up to 2 times (for technical failures)
        strategies = [
            ("youtube_transcript_api", self._fetch_youtube_transcript_api, 2),
            ("yt_dlp", self._fetch_yt_dlp, 2),
            ("playwright", self._fetch_playwright, 2),
        ]

        metadata: dict = {}
        last_error: Exception | None = None

        for name, strategy, max_attempts in strategies:
            for attempt in range(max_attempts):
                try:
                    raw_text, segments, lang, chapters, meta = await strategy(
                        video_id, languages
                    )
                    if segments:
                        metadata.update(meta or {})
                        return raw_text, segments, lang, chapters, metadata
                except TranscriptUnavailableError as e:
                    # No transcript available for this video — do not retry this strategy
                    logger.info(
                        "transcript_unavailable",
                        strategy=name,
                        video_id=video_id,
                        reason=str(e),
                    )
                    break  # break inner attempts loop
                except Exception as e:
                    last_error = e
                    is_last_attempt = attempt == max_attempts - 1
                    if is_last_attempt:
                        logger.warning(
                            "transcript_fetch_failed",
                            strategy=name,
                            video_id=video_id,
                            attempt=attempt + 1,
                            error=str(e),
                        )
                    else:
                        # Exponential backoff with jitter
                        base_delay = 1 * (2 ** attempt)
                        jitter = random.uniform(0, 1)
                        delay = base_delay + jitter
                        logger.info(
                            "transcript_retry",
                            strategy=name,
                            video_id=video_id,
                            attempt=attempt + 1,
                            delay=delay,
                        )
                        await asyncio.sleep(delay)

        # Exhausted all strategies
        raise TranscriptUnavailableError(
            f"Could not fetch transcript for {video_id}. "
            f"Last error: {last_error or 'unknown'}"
        )

    # ------------------------------------------------------------------
    # Strategy 1: youtube-transcript-api (fastest, no browser)
    # ------------------------------------------------------------------

    async def _fetch_youtube_transcript_api(
        self, video_id: str, languages: list[str]
    ) -> tuple[str, list[TranscriptSegment], str | None, list[dict], dict]:
        """Try youtube-transcript-api (pure Python, no browser needed)."""
        from youtube_transcript_api import YouTubeTranscriptApi

        loop = asyncio.get_event_loop()
        try:
            # This is a blocking call, but fast (~200ms)
            transcript_list = await loop.run_in_executor(
                None,
                lambda: YouTubeTranscriptApi.get_transcript(
                    video_id, languages=languages
                ),
            )
        except Exception as e:
            msg = str(e).lower()
            if "transcripts are disabled" in msg or "not available" in msg:
                raise TranscriptUnavailableError(str(e))
            raise

        segments = []
        for item in transcript_list:
            start = item.get("start", 0)
            duration = item.get("duration", 0)
            text = item.get("text", "")
            segments.append(TranscriptSegment(text, start, start + duration))

        raw_text = " ".join(s.text for s in segments)
        detected_lang = transcript_list[0].get("language", languages[0]) if transcript_list else None
        return raw_text, segments, detected_lang, [], {}

    # ------------------------------------------------------------------
    # Strategy 2: yt-dlp
    # ------------------------------------------------------------------

    async def _fetch_yt_dlp(
        self, video_id: str, languages: list[str]
    ) -> tuple[str, list[TranscriptSegment], str | None, list[dict], dict]:
        """Try yt-dlp as fallback."""
        import subprocess

        url = f"https://www.youtube.com/watch?v={video_id}"
        lang_str = ",".join(languages)

        cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-subs",
            "--sub-langs", lang_str,
            "--sub-format", "json3",
            "--convert-subs", "json3",
            "--quiet",
            "--no-warnings",
            "--print", "%(title)s|%(duration)s|%(view_count)s|%(thumbnail)s",
            "-o", "-",
            url,
        ]

        loop = asyncio.get_event_loop()
        try:
            proc = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=30),
            )
        except subprocess.TimeoutExpired:
            raise Exception("yt-dlp timed out")
        except FileNotFoundError:
            raise Exception("yt-dlp not installed")

        if proc.returncode != 0:
            stderr = proc.stderr.lower()
            if "subtitles" in stderr and "not available" in stderr:
                raise TranscriptUnavailableError(proc.stderr)
            raise Exception(f"yt-dlp error: {proc.stderr[:500]}")

        # Parse metadata from first line
        meta_line = proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else ""
        parts = meta_line.split("|")
        metadata = {
            "title": parts[0] if len(parts) > 0 else None,
            "duration": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None,
            "view_count": int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None,
            "thumbnail_url": parts[3] if len(parts) > 3 else None,
        }

        # Try to extract subtitles from yt-dlp auxiliary output (if --write-subs wrote to stdout)
        # This path is not always reliable. yt-dlp usually writes to files:
        # Simpler approach: use yt-dlp --dump-json and parse automatic_captions
        # Re-run with dump-json for captions info
        cmd_json = [
            "yt-dlp",
            "--skip-download",
            "--dump-json",
            "--quiet",
            "--no-warnings",
            url,
        ]

        proc_json = await loop.run_in_executor(
            None,
            lambda: subprocess.run(cmd_json, capture_output=True, text=True, timeout=30),
        )
        if proc_json.returncode != 0:
            raise Exception(f"yt-dlp json error: {proc_json.stderr[:500]}")

        import json
        try:
            info = json.loads(proc_json.stdout.splitlines()[0])
        except (json.JSONDecodeError, IndexError):
            raise Exception("yt-dlp produced invalid JSON")

        # Prefer manual captions, fallback to automatic
        captions = info.get("subtitles", {}) or info.get("automatic_captions", {})

        for lang in languages:
            if lang in captions and captions[lang]:
                # Get the first format that is parseable (JSON3 is best)
                entries = captions[lang]
                json3_entry = next(
                    (e for e in entries if e.get("ext") == "json3"), None
                )
                target = json3_entry or entries[0]
                url = target.get("url")
                if not url:
                    continue

                # Download the subtitle JSON
                import urllib.request
                data = await loop.run_in_executor(
                    None, lambda: urllib.request.urlopen(url, timeout=15).read()
                )
                caption_json = json.loads(data)
                events = caption_json.get("events", [])

                segments = []
                for ev in events:
                    start_ms = ev.get("tStartMs", 0)
                    dur_ms = ev.get("dDurationMs", 0)
                    segs = ev.get("segs", [])
                    text = "".join(s.get("utf8", "") for s in segs if "utf8" in s)
                    if text.strip():
                        segments.append(
                            TranscriptSegment(
                                text.strip(),
                                start_ms / 1000.0,
                                (start_ms + dur_ms) / 1000.0,
                            )
                        )

                raw_text = " ".join(s.text for s in segments)
                return raw_text, segments, lang, [], metadata

        raise TranscriptUnavailableError("No captions found via yt-dlp")

    # ------------------------------------------------------------------
    # Strategy 3: Playwright (last resort, DOM-based)
    # ------------------------------------------------------------------

    async def _fetch_playwright(
        self, video_id: str, languages: list[str]
    ) -> tuple[str, list[TranscriptSegment], str | None, list[dict], dict]:
        """Fetch via Playwright DOM interaction."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _playwright_executor,
            lambda: self._fetch_with_playwright(video_id, languages),
        )

    def _extract_video_id(self, video_url: str) -> str:
        if video_url.startswith(("http://", "https://")):
            import urllib.parse

            parsed = urllib.parse.urlparse(video_url)
            qs = urllib.parse.parse_qs(parsed.query)
            if "v" in qs:
                return qs["v"][0]
            return parsed.path.lstrip("/")
        return video_url

    def _fetch_with_playwright(
        self, video_id: str, languages: list[str]
    ) -> tuple[str, list[TranscriptSegment], str | None, list[dict], dict]:
        url = f"https://www.youtube.com/watch?v={video_id}"
        storage_state_path = os.path.abspath(_STORAGE_STATE_PATH)

        metadata: dict = {}
        segments: list[TranscriptSegment] = []
        lang: str | None = None

        from playwright.sync_api import sync_playwright

        for attempt in range(2):
            pw = sync_playwright().start()
            browser = None
            context = None
            page = None

            try:
                try:
                    browser = pw.chromium.launch(
                        channel="chrome",
                        headless=True,
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--disable-gpu",
                            "--no-sandbox",
                        ],
                    )
                except Exception as launch_exc:
                    logger.debug(
                        "playwright_fallback_chrome",
                        error=str(launch_exc),
                        video_id=video_id,
                    )
                    browser = pw.chromium.launch(
                        headless=True,
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--disable-gpu",
                            "--no-sandbox",
                        ],
                    )

                ctx_kwargs: dict = {"locale": "pt-BR"}
                if os.path.exists(storage_state_path):
                    ctx_kwargs["storage_state"] = storage_state_path

                context = browser.new_context(**ctx_kwargs)
                page = context.new_page()
                page.route("**/*", _route_handler)

                if attempt > 0:
                    logger.info(
                        "playwright_retry", video_id=video_id, attempt=attempt + 1
                    )
                logger.info("playwright_loading", video_id=video_id, url=url)
                page.goto(url, wait_until="domcontentloaded", timeout=30000)

                player_data = page.evaluate(
                    """
                    () => {
                        const r = window.ytInitialPlayerResponse || {};
                        const details = r.videoDetails || {};
                        const thumbs = details.thumbnail?.thumbnails || [];
                        return {
                            metadata: {
                                title: details.title || '',
                                duration: parseInt(details.lengthSeconds || 0),
                                view_count: parseInt(details.viewCount || 0),
                                channel_title: details.author || '',
                                thumbnail_url: thumbs.length ? thumbs[thumbs.length - 1].url : '',
                            },
                        };
                    }
                """
                )
                metadata = player_data.get("metadata", {})

                segments, lang = self._open_transcript_panel(page, languages)

                try:
                    context.storage_state(path=storage_state_path)
                except Exception:
                    pass

            finally:
                if page:
                    page.close()
                if context:
                    context.close()
                if browser:
                    browser.close()
                pw.stop()

            if segments:
                break
            logger.warning(
                "playwright_no_segments",
                video_id=video_id,
                attempt=attempt + 1,
            )

        raw_text = " ".join(s.text for s in segments) if segments else ""
        return raw_text, segments, lang, [], metadata

    def _open_transcript_panel(
        self, page: Any, languages: list[str]
    ) -> tuple[list[TranscriptSegment], str | None]:
        """Expand description, click Show transcript, read segments from DOM."""

        try:
            page.wait_for_selector(
                "#description-inline-expander #expand", timeout=15000
            )
        except Exception:
            logger.warning("description_expand_missing")
            return [], None

        try:
            page.locator("#description-inline-expander #expand").click(timeout=5000)
            page.wait_for_timeout(800)
        except Exception:
            pass

        transcript_clicked = page.evaluate(
            """
            () => {
                const btn = Array.from(document.querySelectorAll('span, button, yt-formatted-string'))
                    .find(el =>
                        /mostrar\\s+transcri|show\\s+transcript/i.test(el.innerText || '')
                        && el.offsetParent !== null
                    );
                if (btn) { btn.click(); return true; }
                return false;
            }
        """
        )

        if not transcript_clicked:
            logger.warning("transcript_button_not_found")
            return [], None

        logger.info("transcript_button_clicked")

        try:
            page.wait_for_selector(
                "transcript-segment-view-model, ytd-transcript-segment-renderer",
                timeout=15000,
            )
        except Exception:
            logger.warning("transcript_segments_not_found")
            return [], None

        segments_data = page.evaluate(
            """
            () => {
                const segs = document.querySelectorAll(
                    'transcript-segment-view-model, ytd-transcript-segment-renderer'
                );
                return Array.from(segs).map(seg => {
                    const lines = seg.innerText.trim().split('\\n').map(l => l.trim()).filter(Boolean);
                    const timestamp = lines.find(l => /^\\d+:\\d+/.test(l)) || '0:00';
                    const text = lines.filter(l =>
                        !/^\\d+:\\d+/.test(l) &&
                        !/^\\d+\\s+(segundo|minuto|hora)/i.test(l)
                    ).join(' ');
                    return { timestamp, text };
                }).filter(s => s.text);
            }
        """
        )

        if not segments_data:
            logger.warning("no_segments_in_panel")
            return [], None

        logger.info(
            "segments_found", count=len(segments_data), video_id="playwright"
        )

        segments = []
        for item in segments_data:
            start = self._parse_timestamp(item["timestamp"])
            segments.append(TranscriptSegment(item["text"], start, start))

        for i in range(len(segments) - 1):
            segments[i].end = segments[i + 1].start

        lang = page.evaluate(
            """
            () => {
                const r = window.ytInitialPlayerResponse || {};
                const tracks = r.captions?.playerCaptionsTracklistRenderer?.captionTracks || [];
                return tracks.length ? tracks[0].languageCode : null;
            }
        """
        )

        return segments, lang

    def _parse_timestamp(self, ts: str) -> float:
        parts = ts.strip().split(":")
        try:
            if len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        except (ValueError, IndexError):
            pass
        return 0.0
