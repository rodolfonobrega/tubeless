"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="",  # No prefix for environment variables
    )

    # Application
    app_name: str = "TubeLess"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/tubeless",
        description="Async database URL for SQLAlchemy",
    )
    database_url_sync: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/tubeless",
        description="Sync database URL for Alembic migrations",
    )
    pool_size: int = 20
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins",
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # LLM Configuration (provider keys are read directly by LiteLLM from env)
    default_model: str = Field(
        default="gpt-4o-mini",
        description="Default model to use",
    )
    default_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Default embedding model",
    )
    # Role-specific models — fall back to default_model if not set
    triage_model: str | None = Field(
        default=None,
        description="Model for fast/cheap tasks: query expansion, ranking, query rewriting",
    )
    summarization_model: str | None = Field(
        default=None,
        description="Model for map-reduce summarization (good context window recommended)",
    )
    answer_model: str | None = Field(
        default=None,
        description="Model for final RAG answer generation (best quality)",
    )
    temperature: float = 0.7
    max_tokens: int = 4096
    reasoning_effort: str | None = Field(
        default=None,
        description="Reasoning effort for supported models: low | medium | high",
    )

    # Vector Store
    vector_dimension: int = Field(
        default=1536,
        description="Dimension of embedding vectors",
    )
    similarity_threshold: float = Field(
        default=0.3,
        description="Minimum similarity score for RAG retrieval",
    )
    top_k_results: int = Field(
        default=5,
        description="Number of chunks to retrieve for RAG",
    )

    # Comments
    max_comments: int = Field(
        default=100,
        description="Max comments to fetch per video (sorted by likes)",
    )

    # Search
    pre_selected_count: int = Field(
        default=3,
        description="Number of videos pre-selected after LLM ranking",
    )
    search_results_per_term: int = Field(
        default=30,
        description="Number of results fetched per search term",
    )
    search_terms_per_language: int = Field(
        default=3,
        description="Number of search terms generated per language (PT + EN)",
    )

    # Text Processing
    chunk_size: int = Field(
        default=1500,
        description="Target chunk size in tokens",
    )
    chunk_overlap: int = Field(
        default=200,
        description="Overlap between chunks in tokens",
    )
    max_chunk_size: int = Field(
        default=2000,
        description="Maximum chunk size in tokens",
    )

    # Summarization
    summary_max_length: int = Field(
        default=800,
        description="Max output tokens for individual chunk summaries",
    )
    consolidated_summary_max_length: int = Field(
        default=4000,
        description="Max output tokens for consolidated cross-video synthesis",
    )

    # JWT Authentication
    secret_key: str = Field(
        default="change-this-secret-key-in-production",
        description="Secret key for JWT encoding",
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # WebSocket
    wsHeartbeat_interval: int = 30

    # YouTube Processing
    video_quality: str = "best"
    subtitle_languages: list[str] = Field(
        default=["en", "en-US", "en-GB", "pt", "pt-BR"],
        description="Preferred subtitle languages",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("subtitle_languages", mode="before")
    @classmethod
    def parse_subtitle_languages(cls, v: str | list[str]) -> list[str]:
        """Parse subtitle languages from string or list."""
        if isinstance(v, str):
            return [lang.strip() for lang in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
