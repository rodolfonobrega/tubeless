"""Video ranking service: uses LLM to filter and rank videos by relevance."""

import json
import logging
import re

from app.core.config import get_settings
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)
settings = get_settings()

_TEMPORAL_PATTERN = re.compile(
    r"\b(202[4-9]|203\d|novo|novos|nova|novas|recente|recentes|latest|new|recent|best \d{4}|melhores \d{4})\b",
    re.IGNORECASE,
)


def _is_temporal_query(query: str) -> bool:
    return bool(_TEMPORAL_PATTERN.search(query))


class VideoRankingService:
    def __init__(self) -> None:
        from app.services.llm_service import _eff
        self.llm = LLMService(model=_eff("triage_model", settings.triage_model) or _eff("default_model", settings.default_model))

    async def rank(
        self,
        query: str,
        videos: list[dict],
        pre_selected_count: int = 3,
    ) -> list[dict]:
        """Rank videos by relevance to query and mark top N as pre-selected."""
        if not videos:
            return []

        is_temporal = _is_temporal_query(query)

        numbered = [
            {
                "i": i,
                "t": v["title"],
                "d": (v.get("description") or "")[:150],
                "p": (v.get("published_at") or "")[:10],
            }
            for i, v in enumerate(videos)
        ]

        temporal_instruction = (
            "\nIMPORTANT: This query is time-sensitive. Penalize videos published before 2024 "
            "(use p field). Prefer recent content."
            if is_temporal else ""
        )

        prompt = f"""The user searched for: "{query}"
{temporal_instruction}
Rate each video's relevance 0-10. Output ONLY a JSON array, one object per relevant video (score >= 4).
Each object: {{"i": index, "s": score, "r": "reason max 8 words"}}. Sort by score descending.

Videos:
{json.dumps(numbered, ensure_ascii=False)}"""

        try:
            response = await self.llm.completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=4000,
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            rankings = json.loads(content)
        except Exception as e:
            logger.warning(f"Video ranking failed, returning unranked: {e}")
            for v in videos:
                v["relevance_score"] = 5
                v["relevance_reason"] = ""
                v["pre_selected"] = False
            for v in videos[:pre_selected_count]:
                v["pre_selected"] = True
            return videos

        index_to_ranking = {
            r.get("i", r.get("index")): r
            for r in rankings
            if r.get("s", r.get("score", 0)) >= 4
        }

        ranked = []
        for i, video in enumerate(videos):
            ranking = index_to_ranking.get(i)
            if ranking is None:
                continue
            ranked.append({
                **video,
                "relevance_score": ranking.get("s", ranking.get("score", 5)),
                "relevance_reason": ranking.get("r", ranking.get("reason", "")),
                "pre_selected": False,
            })

        ranked.sort(key=lambda v: v["relevance_score"], reverse=True)

        for video in ranked[:pre_selected_count]:
            video["pre_selected"] = True

        return ranked
