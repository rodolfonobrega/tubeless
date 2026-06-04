"""Summarization service using map-reduce pattern."""

import logging
from typing import Any

from app.core.config import get_settings
from app.services.chunking_service import Chunk
from app.services.llm_service import LLMService

settings = get_settings()
logger = logging.getLogger(__name__)


class VideoSummaryResult:
    """Result of video summarization."""

    def __init__(
        self,
        summary_text: str,
        key_points: list[dict[str, Any]],
        topics: list[str],
    ) -> None:
        self.summary_text = summary_text
        self.key_points = key_points
        self.topics = topics


class ConsolidatedSummaryResult:
    """Result of cross-video consolidation."""

    def __init__(
        self,
        summary_text: str,
        key_themes: list[dict[str, Any]],
        consensus_points: list[str],
        differing_viewpoints: list[dict[str, Any]],
        contradictions: list[dict[str, Any]] | None = None,
    ) -> None:
        self.summary_text = summary_text
        self.key_themes = key_themes
        self.consensus_points = consensus_points
        self.differing_viewpoints = differing_viewpoints
        self.contradictions = contradictions or []


class SummarizationService:
    """Service for summarizing transcripts using map-reduce pattern."""

    def __init__(self) -> None:
        """Initialize the summarization service."""
        from app.services.llm_service import _eff
        self.llm_service = LLMService(model=_eff("summarization_model", settings.summarization_model) or _eff("default_model", settings.default_model))

    async def summarize_chunks(
        self,
        chunks: list[Chunk],
        video_title: str = "",
    ) -> VideoSummaryResult:
        """Summarize video using map-reduce on chunks.

        Args:
            chunks: List of transcript chunks.
            video_title: Title of the video for context.

        Returns:
            VideoSummaryResult with summary, key points, and topics.
        """
        if not chunks:
            raise ValueError("No chunks to summarize")

        # Step 1: Map - Summarize each chunk
        logger.info(f"Map phase: Summarizing {len(chunks)} chunks")
        chunk_summaries = await self._map_summaries(chunks, video_title)

        # Step 2: Reduce - Combine chunk summaries
        logger.info("Reduce phase: Combining chunk summaries")
        final_summary = await self._reduce_summaries(chunk_summaries, video_title)

        return final_summary

    async def _map_summaries(
        self,
        chunks: list[Chunk],
        video_title: str,
    ) -> list[str]:
        """Summarize each chunk in parallel with a semaphore to limit concurrency."""
        import asyncio

        sem = asyncio.Semaphore(5)  # Limit concurrent LLM calls to 5

        async def _summarize_one(i: int, chunk: Chunk) -> str:
            prompt = self._get_chunk_summary_prompt(
                chunk.content,
                chunk.chunk_index,
                len(chunks),
                video_title,
            )
            async with sem:
                try:
                    response = await self.llm_service.completion(
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You are an expert at summarizing video transcripts. "
                                    "Extract key information clearly and concisely."
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.3,
                        max_tokens=800,
                    )
                    summary = response.choices[0].message.content
                    logger.debug(f"Summarized chunk {i+1}/{len(chunks)}")
                    return summary
                except Exception as e:
                    logger.error(f"Error summarizing chunk {i}: {e}")
                    return f"[Error summarizing chunk {i}]"

        tasks = [_summarize_one(i, chunk) for i, chunk in enumerate(chunks)]
        summaries = await asyncio.gather(*tasks)
        return list(summaries)

    async def _reduce_summaries(
        self,
        chunk_summaries: list[str],
        video_title: str,
    ) -> VideoSummaryResult:
        """Combine chunk summaries into a final video summary."""
        combined_summaries = "\n\n".join(
            f"Part {i+1}:\n{summary}"
            for i, summary in enumerate(chunk_summaries)
        )

        prompt = f"""Based on the following segment summaries from a video titled "{video_title}", create:

1. A comprehensive summary (500-800 words)
2. A list of 5-7 key points with timestamps if available
3. Main topics covered

Segment summaries:
{combined_summaries}

Format your response as JSON:
{{
    "summary_text": "...",
    "key_points": [
        {{"point": "...", "timestamp": "..."}}
    ],
    "topics": ["...", "..."]
}}"""

        try:
            response = await self.llm_service.completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at synthesizing information from video content.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=16000,
            )

            content = response.choices[0].message.content

            # Try to parse JSON response
            import json

            try:
                # Extract JSON from markdown code blocks if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                result_data = json.loads(content)
                return VideoSummaryResult(
                    summary_text=result_data.get("summary_text", content),
                    key_points=result_data.get("key_points", []),
                    topics=result_data.get("topics", []),
                )
            except json.JSONDecodeError:
                # Fallback: parse the text response
                return VideoSummaryResult(
                    summary_text=content,
                    key_points=[],
                    topics=[],
                )

        except Exception as e:
            logger.error(f"Error reducing summaries: {e}")
            raise

    async def consolidate_video_summaries(
        self,
        video_summaries: list[dict[str, Any]],
        project_query: str,
    ) -> ConsolidatedSummaryResult:
        """Consolidate video summaries into a cross-video synthesis.

        Uses the full context window — models have 128K-200K+ tokens.
        Output budget scales with video count to avoid information loss.
        """
        if not video_summaries:
            raise ValueError("No video summaries to consolidate")

        summaries_text = "\n\n".join(
            f"Video: {v.get('title', 'Unknown')}\nSummary: {v.get('summary_text', '')}\n"
            for v in video_summaries
        )

        # Scale output budget: more videos → more themes/consensus/viewpoints to capture
        n = len(video_summaries)
        output_budget = max(8000, min(32000, n * 1000))
        logger.info(f"Consolidating {n} videos with output budget {output_budget} tokens")

        prompt = f"""Analyze the following {n} video summaries related to the query "{project_query}" and create a thorough cross-video synthesis.

Be comprehensive — capture ALL themes, consensus points, differing viewpoints, and contradictions. Do not omit anything important.

Video summaries:
{summaries_text}

Format your response as JSON:
{{
    "summary_text": "Comprehensive synthesis covering all videos...",
    "key_themes": [
        {{"theme": "...", "sources": ["Video1", "Video2"], "description": "..."}}
    ],
    "consensus_points": ["Point that all/most videos agree on", "..."],
    "differing_viewpoints": [
        {{"topic": "...", "viewpoints": [{{"source": "Video title", "position": "..."}}]}}
    ],
    "contradictions": [
        {{
            "topic": "Topic where videos directly contradict each other",
            "claim_a": "First claim",
            "source_a": "Video title that makes claim A",
            "claim_b": "Contradicting claim",
            "source_b": "Video title that makes claim B"
        }}
    ]
}}

For contradictions: only include DIRECT contradictions where videos make opposing factual claims. Leave the array empty if there are no true contradictions."""

        try:
            import json

            response = await self.llm_service.completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at synthesizing information from multiple sources. Be thorough — capture all meaningful themes, agreements, and disagreements across all videos.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=output_budget,
            )

            content = response.choices[0].message.content

            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                result_data = json.loads(content)
                return ConsolidatedSummaryResult(
                    summary_text=result_data.get("summary_text", content),
                    key_themes=result_data.get("key_themes", []),
                    consensus_points=result_data.get("consensus_points", []),
                    differing_viewpoints=result_data.get("differing_viewpoints", []),
                    contradictions=result_data.get("contradictions", []),
                )
            except json.JSONDecodeError:
                return ConsolidatedSummaryResult(
                    summary_text=content,
                    key_themes=[],
                    consensus_points=[],
                    differing_viewpoints=[],
                    contradictions=[],
                )

        except Exception as e:
            logger.error(f"Error consolidating summaries: {e}")
            raise

    def _get_chunk_summary_prompt(
        self,
        chunk_text: str,
        chunk_index: int,
        total_chunks: int,
        video_title: str,
    ) -> str:
        """Generate prompt for summarizing a single chunk."""
        return f"""Summarize this transcript segment (part {chunk_index + 1} of {total_chunks}) from "{video_title}".

Focus on:
- Main points discussed
- Key information or insights
- Any examples or data mentioned

Transcript segment:
{chunk_text}

Provide a clear, concise summary."""
