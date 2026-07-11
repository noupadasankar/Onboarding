"""OpenAI embedding provider.

Requires the ``openai`` package (``pip install openai>=1.40``).
Implements:
  * Async batch embedding via ``AsyncOpenAI.embeddings.create``.
  * Retry with exponential backoff on rate-limit and transient errors.
  * Timeout support.

If the openai package is not installed, instantiating this class raises
``ImportError`` with an install hint.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from app.embeddings.providers.base_provider import (
    BaseEmbeddingProvider,
    EmbeddingProviderError,
)
from app.core.logging import get_logger

if TYPE_CHECKING:
    pass

_log = get_logger()

# ── Optional import ───────────────────────────────────────────────────────────

try:
    from openai import (
        AsyncOpenAI,
        AuthenticationError,
        BadRequestError,
        RateLimitError,
        APITimeoutError,
        APIConnectionError,
        APIStatusError,
    )
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False

# Retry constants
_MAX_RETRIES = 3
_BASE_DELAY = 1.0   # seconds
_MAX_DELAY = 30.0   # seconds


class OpenAIProvider(BaseEmbeddingProvider):
    """OpenAI embedding provider (text-embedding-3-small / text-embedding-3-large / ada-002).

    Args:
        api_key: OpenAI API key. Defaults to ``OPENAI_API_KEY`` env var.
        model: Model identifier. Default ``text-embedding-3-small``.
        dimensions: Vector size. Default 1536. Only supported by v3 models.
        timeout: HTTP timeout in seconds. Default 60.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
        timeout: float = 60.0,
    ) -> None:
        if not _HAS_OPENAI:
            raise ImportError(
                "openai package is required for OpenAIProvider. "
                "Install it with: pip install 'openai>=1.40,<2'"
            )

        from app.core.config import get_settings
        key = api_key or get_settings().openai_api_key
        if not key:
            raise ValueError(
                "OPENAI_API_KEY is not set. "
                "Add it to your .env file or pass api_key= explicitly."
            )

        self._client = AsyncOpenAI(api_key=key, timeout=timeout)  # type: ignore[arg-type]
        self._model = model
        self._dimensions = dimensions
        self._timeout = timeout

        # Ada-002 does not support the `dimensions` parameter
        self._supports_dimensions = "3-" in model

    # ── BaseEmbeddingProvider ─────────────────────────────────────────────────

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed *texts* via the OpenAI API with retry on transient failures."""
        return await self._embed_with_retry(texts)

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _embed_with_retry(self, texts: list[str]) -> list[list[float]]:
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                return await self._call_api(texts)
            except RateLimitError as exc:
                last_exc = exc
                delay = min(_BASE_DELAY * (2 ** attempt), _MAX_DELAY)
                _log.warning(
                    "openai_rate_limit",
                    attempt=attempt + 1,
                    retry_after_s=delay,
                )
                await asyncio.sleep(delay)
            except (APITimeoutError, APIConnectionError) as exc:
                last_exc = exc
                delay = min(_BASE_DELAY * (2 ** attempt), _MAX_DELAY)
                _log.warning(
                    "openai_transient_error",
                    error=str(exc),
                    attempt=attempt + 1,
                    retry_after_s=delay,
                )
                await asyncio.sleep(delay)
            except (AuthenticationError, BadRequestError) as exc:
                # Non-retryable — fail immediately
                raise EmbeddingProviderError(f"OpenAI non-retryable error: {exc}") from exc
            except APIStatusError as exc:
                last_exc = exc
                if exc.status_code and exc.status_code >= 500:
                    delay = min(_BASE_DELAY * (2 ** attempt), _MAX_DELAY)
                    _log.warning(
                        "openai_server_error",
                        status=exc.status_code,
                        attempt=attempt + 1,
                        retry_after_s=delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise EmbeddingProviderError(f"OpenAI API error {exc.status_code}: {exc}") from exc

        raise EmbeddingProviderError(
            f"OpenAI embedding failed after {_MAX_RETRIES} attempts: {last_exc}"
        ) from last_exc

    async def _call_api(self, texts: list[str]) -> list[list[float]]:
        kwargs: dict = {"model": self._model, "input": texts}
        if self._supports_dimensions:
            kwargs["dimensions"] = self._dimensions

        response = await self._client.embeddings.create(**kwargs)

        # Response items are ordered by index
        ordered = sorted(response.data, key=lambda e: e.index)
        return [item.embedding for item in ordered]
