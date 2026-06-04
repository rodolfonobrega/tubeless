"""HyPE service: Hypothetical Pseudo-Embeddings.

Generates hypothetical questions that a chunk could answer,
then creates embeddings for those questions at index-time.
These compete with real chunk embeddings at query-time via RRF.
"""

import asyncio
from typing import Any

from app.services.llm_service import LLMService


class HyPEService:
    """Service for generating and embedding hypothetical questions per chunk."""

    def __init__(self) -> None:
        self.llm = LLMService()

    async def generate_questions(
        self,
        chunk_content: str,
        video_title: str = "",
        n_questions: int = 3,
    ) -> list[str]:
        """Generate hypothetical questions that this chunk answers."""
        prompt = f"""Given this transcript segment{f' from "{video_title}"' if video_title else ""}, generate {n_questions} concise questions that this segment directly answers.

Transcript segment:
{chunk_content}

Return ONLY a JSON array of strings, no extra text.
Example: ["What is X?", "How does Y work?", "Why is Z important?"]
"""
        try:
            response = await self.llm.completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300,
            )
            import json
            content = response.choices[0].message.content.strip()
            # Strip markdown if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            questions = json.loads(content)
            if isinstance(questions, list) and all(isinstance(q, str) for q in questions):
                return questions[:n_questions]
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"HyPE question generation failed: {e}")

        # Fallback: extract sentences with question marks (very crude)
        return []

    async def generate_questions_for_chunks(
        self,
        chunks: list[tuple[Any, str]],  # list of (chunk_id, chunk_content)
        video_title: str = "",
        n_questions: int = 3,
        max_concurrent: int = 5,
    ) -> list[tuple[Any, list[str]]]:
        """Generate questions for multiple chunks in parallel."""
        sem = asyncio.Semaphore(max_concurrent)

        async def _for_one(chunk_id: Any, content: str) -> tuple[Any, list[str]]:
            async with sem:
                qs = await self.generate_questions(content, video_title, n_questions)
                return (chunk_id, qs)

        tasks = [_for_one(cid, content) for cid, content in chunks]
        return await asyncio.gather(*tasks)
