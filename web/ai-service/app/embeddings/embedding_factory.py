"""Embedding provider factory.

Maps provider names to concrete provider classes.
Follows the Open/Closed Principle: add a new provider by registering it
in ``_REGISTRY`` — no existing code changes.

Usage::

    from app.embeddings.embedding_factory import EmbeddingFactory

    provider = EmbeddingFactory.create()               # reads EMBEDDING_PROVIDER from settings
    provider = EmbeddingFactory.create("openai")       # explicit name
    provider = EmbeddingFactory.create("local")        # deterministic, no API key
"""
from __future__ import annotations

from app.embeddings.providers.base_provider import BaseEmbeddingProvider
from app.embeddings.providers.anthropic_provider import AnthropicProvider
from app.embeddings.providers.local_provider import LocalProvider
from app.embeddings.providers.openai_provider import OpenAIProvider
from app.embeddings.providers.voyage_provider import VoyageProvider

# Registry: name → class
_REGISTRY: dict[str, type[BaseEmbeddingProvider]] = {
    "openai": OpenAIProvider,
    "voyage": VoyageProvider,
    "local": LocalProvider,
    "anthropic": AnthropicProvider,
}


class EmbeddingFactory:
    """Instantiates the correct embedding provider from a name string."""

    @classmethod
    def create(cls, provider_name: str | None = None) -> BaseEmbeddingProvider:
        """Return a new provider instance.

        Args:
            provider_name: One of ``openai``, ``voyage``, ``local``,
                ``anthropic``. When *None*, reads ``EMBEDDING_PROVIDER``
                from settings (default ``local``).

        Raises:
            ValueError: If *provider_name* is not in the registry.
            ImportError: If the provider's optional package is not installed.
            ValueError: If a required API key is missing.
        """
        from app.core.config import get_settings

        name = (provider_name or get_settings().embedding_provider).lower().strip()
        cls_= _REGISTRY.get(name)
        if cls_ is None:
            available = ", ".join(sorted(_REGISTRY))
            raise ValueError(
                f"Unknown embedding provider {name!r}. "
                f"Available: {available}"
            )
        return cls_()

    @classmethod
    def available_providers(cls) -> list[str]:
        """Return the list of registered provider names."""
        return sorted(_REGISTRY)
