"""Abstract base class for all embedding providers.

Every provider must implement three properties and one method.
The rest of the embedding stack (service, pipeline, factory) depends
only on this interface, never on a concrete implementation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    """Common interface for all embedding back-ends.

    Usage::

        provider = OpenAIProvider()
        vectors = await provider.embed_batch(["text one", "text two"])
        # vectors: list[list[float]], len == 2
    """

    # ── Abstract API ──────────────────────────────────────────────────────────

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts and return their vectors.

        Args:
            texts: Non-empty list of strings. Callers guarantee no empty strings.

        Returns:
            A list of float vectors, one per input text, in the same order.

        Raises:
            EmbeddingProviderError: On unrecoverable API or validation errors.
        """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Short identifier used in logs and stored on EmbeddedChunk."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Full model identifier (e.g. ``text-embedding-3-small``)."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Output vector size for this model configuration."""

    # ── Default helpers ───────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model_name!r}, dims={self.dimensions})"


# ── Shared exception ──────────────────────────────────────────────────────────

class EmbeddingProviderError(RuntimeError):
    """Raised when an embedding provider returns an unrecoverable error."""
