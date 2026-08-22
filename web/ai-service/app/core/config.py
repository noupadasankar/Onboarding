"""Typed application settings — the single source of truth for all configuration.

Every environment variable is read here and only here. Other modules import
`get_settings()` and access the typed object; they never call `os.environ`
directly.

Settings are grouped by concern so it is obvious which increment activates
each block. Optional fields default to empty string / sensible value so the
application does not fail at startup for settings that are not yet needed.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_env: str = Field(default="development")
    app_port: int = Field(default=8100)

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = Field(default="info")

    # ── Security — internal gateway token ─────────────────────────────────────
    # Required: the Node backend must present this on every request.
    internal_service_token: str = Field(min_length=1)
    # Configurable so header name can be rotated without code changes.
    token_header_name: str = Field(default="X-Internal-Token")

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Browsers never call this service directly; CORS is for local debugging.
    allowed_origins: str = Field(default="")

    # ── Vector database ───────────────────────────────────────────────────────
    chroma_url: str = Field(default="http://localhost:8200")
    chroma_collection: str = Field(default="hr_onboarding_documents")
    chroma_tenant: str = Field(default="default_tenant")
    chroma_database: str = Field(default="default_database")
    # "http" uses the HTTP client (remote server); "memory" uses ephemeral in-process client (tests/dev)
    chroma_mode: str = Field(default="http")

    # ── LLM providers ─────────────────────────────────────────────────────────
    anthropic_api_key: str = Field(default="")
    openai_api_key: str = Field(default="")
    # Optional: override the OpenAI API base URL (e.g. https://api.groq.com/openai/v1 for Groq)
    openai_base_url: str = Field(default="")
    # Provider: openai | anthropic | local (default local — no API key required)
    llm_provider: str = Field(default="local")
    llm_model: str = Field(default="gpt-4.1")
    llm_temperature: float = Field(default=0.0)
    llm_max_tokens: int = Field(default=1024)
    llm_timeout: int = Field(default=60)
    llm_max_retries: int = Field(default=3)
    # Max conversation turns sent as history to the LLM (each turn = 2 messages)
    conversation_history_window: int = Field(default=10)

    # ── Redis — conversation memory ───────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0")

    # ── Data storage ──────────────────────────────────────────────────────────
    # Absolute or relative path to the HR documents directory.
    # When set, uploaded originals are saved to disk after successful ingestion.
    # Leave empty to skip disk persistence (default for tests and CI).
    hr_documents_dir: str = Field(default="")

    # ── Chunk export ──────────────────────────────────────────────────────────
    # When set, the chunk pipeline writes a JSON debug file per document to
    # this directory. Very useful during development; leave empty in production.
    chunk_export_dir: str = Field(default="")

    # ── Embeddings ────────────────────────────────────────────────────────────
    # Provider: openai | voyage | local (default local — no API key required)
    embedding_provider: str = Field(default="local")
    # Model identifier — must match the chosen provider's supported models.
    embedding_model: str = Field(default="text-embedding-3-small")
    # Output vector dimensions (provider + model dependent).
    embedding_dimensions: int = Field(default=1536)
    # Number of texts sent in a single embedding API call.
    embedding_batch_size: int = Field(default=100)
    # HTTP timeout in seconds for embedding API calls.
    embedding_timeout: int = Field(default=60)
    # When set, the embedding pipeline writes a JSON debug file per document.
    embedding_export_dir: str = Field(default="")

    # ── Derived helpers ───────────────────────────────────────────────────────
    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Return a memoized, validated Settings instance (one per process)."""
    return Settings()  # type: ignore[call-arg]
