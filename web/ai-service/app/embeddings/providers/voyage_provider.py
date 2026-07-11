"""Voyage AI embedding provider (stub).

Voyage AI (https://www.voyageai.com/) produces state-of-the-art embeddings
optimised for retrieval. Anthropic recommends Voyage for production RAG.

Activate by setting:
    EMBEDDING_PROVIDER=voyage
    VOYAGE_API_KEY=<your-key>
    EMBEDDING_MODEL=voyage-3-large   # or voyage-3, voyage-code-3, …

Requires: pip install voyageai>=0.2

This stub raises ``NotImplementedError`` until the voyageai package is
installed and configured.
"""
from __future__ import annotations

from app.embeddings.providers.base_provider import (
    BaseEmbeddingProvider,
    EmbeddingProviderError,
)

try:
    import voyageai  # type: ignore[import-untyped]
    _HAS_VOYAGE = True
except ImportError:
    _HAS_VOYAGE = False


class VoyageProvider(BaseEmbeddingProvider):
    """Voyage AI embedding provider.

    Args:
        api_key: Voyage API key. Defaults to ``VOYAGE_API_KEY`` env var.
        model: Model name. Default ``voyage-3-large``.
        dimensions: Not all Voyage models support custom dimensions; consult
            their docs. This value is stored on the EmbeddedChunk.
    """

    # Default dimensions for voyage-3-large
    _DEFAULT_DIMS = 1024

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "voyage-3-large",
        dimensions: int = _DEFAULT_DIMS,
    ) -> None:
        if not _HAS_VOYAGE:
            raise ImportError(
                "voyageai package is required for VoyageProvider. "
                "Install it with: pip install 'voyageai>=0.2'"
            )
        import os
        key = api_key or os.environ.get("VOYAGE_API_KEY", "")
        if not key:
            raise ValueError(
                "VOYAGE_API_KEY is not set. "
                "Add it to your .env file or pass api_key= explicitly."
            )
        self._client = voyageai.AsyncClient(api_key=key)
        self._model = model
        self._dimensions = dimensions

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            result = await self._client.embed(texts, model=self._model, input_type="document")
            return result.embeddings
        except Exception as exc:
            raise EmbeddingProviderError(f"Voyage AI embedding failed: {exc}") from exc

    @property
    def provider_name(self) -> str:
        return "voyage"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions
