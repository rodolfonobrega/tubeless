"""Query expansion service: generates search terms from a user query."""

import json
import logging

from app.core.config import get_settings
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)
settings = get_settings()


class QueryExpansionService:
    def __init__(self) -> None:
        from app.services.llm_service import _eff
        self.llm = LLMService(model=_eff("triage_model", settings.triage_model) or _eff("default_model", settings.default_model))

    async def expand(self, query: str, terms_per_language: int = 3) -> list[str]:
        """Generate search terms in PT and EN for the given query."""
        prompt = f"""Given the user query: "{query}"

Generate {terms_per_language} YouTube search terms in Portuguese and {terms_per_language} in English.
Return ONLY a JSON array of strings, no explanation.

Example output:
["como aprender inglês rápido", "método eficaz aprender inglês", "dicas inglês fluente",
 "how to learn english fast", "best english learning method", "english fluency tips"]"""

        try:
            response = await self.llm.completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300,
            )
            content = response.choices[0].message.content.strip()
            # Strip markdown code block if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            terms = json.loads(content)
            if isinstance(terms, list) and all(isinstance(t, str) for t in terms):
                return terms
        except Exception as e:
            logger.warning(f"Query expansion failed, falling back to original query: {e}")

        return [query]
