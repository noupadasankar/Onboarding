"""Anthropic embedding provider (placeholder).

As of 2026-07 Anthropic does not offer a public embedding API endpoint.
For production RAG with Anthropic models, use Voyage AI (voyage_provider.py)
which is Anthropic's recommended embedding partner.

This file is a placeholder to satisfy the project's provider registry.
It raises ``NotImplementedError`` when instantiated.
"""
from __future__ import annotations

from app.embeddings.providers.base_provider import BaseEmbeddingProvider


class AnthropicProvider(BaseEmbeddingProvider):
    """Placeholder — Anthropic does not currently offer a public embedding API.

    Use ``VoyageProvider`` instead (Anthropic's recommended partner for embeddings).
    """

    def __init__(self) -> None:
        raise NotImplementedError(
            "Anthropic does not offer a public embedding API. "
            "Use EMBEDDING_PROVIDER=voyage with the Voyage AI provider instead. "
            "See: https://www.voyageai.com/"
        )

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        raise NotImplementedError

    @property
    def provider_name(self) -> str:  # pragma: no cover
        return "anthropic"

    @property
    def model_name(self) -> str:  # pragma: no cover
        return ""

    @property
    def dimensions(self) -> int:  # pragma: no cover
        return 0
