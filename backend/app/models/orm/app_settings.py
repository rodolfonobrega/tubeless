"""User-configurable application settings persisted in DB."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.orm.base import BaseModel


class AppSettings(BaseModel):
    """Key-value store for user overrides of application settings.

    Only keys in USER_CONFIGURABLE_KEYS are accepted.
    When value matches the .env default, the row is deleted (no redundant storage).
    """

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Keys the user is allowed to change via the settings API
    USER_CONFIGURABLE_KEYS: set[str] = {
        "default_model",
        "default_embedding_model",
        "triage_model",
        "summarization_model",
        "answer_model",
        "temperature",
        "max_tokens",
        "reasoning_effort",
        "search_results_per_term",
        "pre_selected_count",
        "top_k_results",
        "similarity_threshold",
    }
