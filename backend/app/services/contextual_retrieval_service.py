"""Contextual Retrieval service: enriches chunk content with video summary context."""

from typing import Any


class ContextualRetrievalService:
    """Service for enriching transcript chunks with video context before embedding."""

    def build_contextual_content(
        self,
        chunk_content: str,
        chunk_start_time: float | None,
        video_title: str,
        video_summary: str,
        key_points: list[dict[str, Any]],
    ) -> str:
        """Build contextual content by prepending video context to chunk text.

        Uses the video summary and nearby key_points to give the chunk context.
        """
        context_parts = [f"Vídeo: '{video_title}'."]

        # Add a brief summary if available
        if video_summary:
            # Truncate summary to ~200 chars to keep context lean
            short_summary = video_summary[:200].rstrip()
            if len(video_summary) > 200:
                short_summary += "..."
            context_parts.append(f"Resumo do vídeo: {short_summary}")

        # Find key_points near this chunk's start time (within 60s)
        nearby_points = []
        if chunk_start_time is not None:
            for kp in key_points:
                ts = kp.get("timestamp")
                if isinstance(ts, (int, float, str)):
                    try:
                        t = float(ts)
                        if abs(t - chunk_start_time) <= 120:  # within 2 minutes
                            nearby_points.append(kp.get("point", ""))
                    except (ValueError, TypeError):
                        continue

        if nearby_points:
            points_text = " | ".join(p for p in nearby_points[:3] if p)
            context_parts.append(f"Pontos-chave próximos: {points_text}")

        context = " ".join(context_parts)
        return f"{context}\n\nTrecho da transcrição:\n{chunk_content}"
