"""Embedding service — orchestrates batch embedding with validation and cache.

Responsibilities:
  1. Accept a list of Chunk objects.
  2. Filter out chunks that are empty or exceed the model's token limit.
  3. Split into batches of ``batch_size``.
  4. Call the embedding provider once per batch.
  5. Validate each returned vector (dimensions, NaN, empty).
  6. Optionally serve from an in-memory SHA-256 cache (avoid re-embedding).
  7. Return EmbeddedChunk objects.

No vector database, no Chroma, no search.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.embeddings.providers.base_provider import BaseEmbeddingProvider, EmbeddingProviderError
from app.embeddings.token_counter import count_tokens, max_input_tokens
from app.models.chunk import Chunk
from app.models.embedded_chunk import EmbeddedChunk

_log = get_logger()


# ── Configuration dataclass ───────────────────────────────────────────────────

@dataclass
class EmbeddingConfig:
    """Configuration for a single embedding run."""

    batch_size: int = 100
    """Number of texts sent to the provider in a single API call."""

    enable_cache: bool = True
    """If True, identical texts reuse previously computed vectors."""


# ── Embedding service ─────────────────────────────────────────────────────────

class EmbeddingService:
    """Converts Chunk objects into EmbeddedChunk objects via a provider.

    Args:
        provider: Any concrete :class:`BaseEmbeddingProvider` implementation.
    """

    def __init__(self, provider: BaseEmbeddingProvider) -> None:
        self._provider = provider
        # SHA-256(text) → embedding vector
        self._cache: dict[str, list[float]] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    async def embed_chunks(
        self,
        chunks: list[Chunk],
        config: EmbeddingConfig | None = None,
    ) -> list[EmbeddedChunk]:
        """Embed *chunks* and return :class:`EmbeddedChunk` objects.

        Chunks that are empty, exceed the model's token limit, or produce
        invalid vectors are skipped (logged as warnings).

        Args:
            chunks: Validated Chunk objects from Increment 4.
            config: Optional configuration. Defaults to ``EmbeddingConfig()``.

        Returns:
            Ordered list of EmbeddedChunk objects (may be shorter than *chunks*
            if some were skipped).
        """
        cfg = config or EmbeddingConfig()
        if not chunks:
            return []

        model = self._provider.model_name
        token_limit = max_input_tokens(model)

        # ── 1. Filter invalid chunks ───────────────────────────────────────
        valid_chunks: list[Chunk] = []
        for c in chunks:
            if not c.text or not c.text.strip():
                _log.warning("embed_skip_empty", chunk_id=c.chunk_id)
                continue
            tc = c.token_count or count_tokens(c.text, model)
            if tc > token_limit:
                _log.warning(
                    "embed_skip_too_long",
                    chunk_id=c.chunk_id,
                    token_count=tc,
                    limit=token_limit,
                )
                continue
            valid_chunks.append(c)

        if not valid_chunks:
            return []

        # ── 2. Cache lookup ───────────────────────────────────────────────
        texts = [c.text for c in valid_chunks]
        cache_keys = [_sha256(t) for t in texts]

        to_embed_indexes: list[int] = []
        cached_vectors: dict[int, list[float]] = {}

        if cfg.enable_cache:
            for i, key in enumerate(cache_keys):
                if key in self._cache:
                    cached_vectors[i] = self._cache[key]
                else:
                    to_embed_indexes.append(i)
        else:
            to_embed_indexes = list(range(len(valid_chunks)))

        _log.info(
            "embed_start",
            total=len(valid_chunks),
            cache_hits=len(cached_vectors),
            to_embed=len(to_embed_indexes),
            provider=self._provider.provider_name,
            model=model,
        )

        # ── 3. Batch embed ────────────────────────────────────────────────
        new_vectors: dict[int, list[float]] = {}

        if to_embed_indexes:
            texts_to_embed = [texts[i] for i in to_embed_indexes]
            batches = _make_batches(texts_to_embed, cfg.batch_size)

            flat_vectors: list[list[float]] = []
            for batch in batches:
                try:
                    vecs = await self._provider.embed_batch(batch)
                    flat_vectors.extend(vecs)
                except EmbeddingProviderError as exc:
                    _log.error("embed_batch_failed", error=str(exc))
                    raise

            for local_i, orig_i in enumerate(to_embed_indexes):
                vec = flat_vectors[local_i]
                new_vectors[orig_i] = vec
                if cfg.enable_cache:
                    self._cache[cache_keys[orig_i]] = vec

        # ── 4. Assemble results ───────────────────────────────────────────
        all_vectors: dict[int, list[float]] = {**cached_vectors, **new_vectors}

        embedded: list[EmbeddedChunk] = []
        for i, chunk in enumerate(valid_chunks):
            vec = all_vectors.get(i)
            if vec is None:
                _log.warning("embed_missing_vector", chunk_id=chunk.chunk_id, index=i)
                continue
            if not _validate_vector(vec, self._provider.dimensions):
                _log.warning(
                    "embed_invalid_vector",
                    chunk_id=chunk.chunk_id,
                    got_dims=len(vec),
                    expected_dims=self._provider.dimensions,
                )
                continue

            embedded.append(
                EmbeddedChunk(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    embedding=vec,
                    dimensions=len(vec),
                    provider=self._provider.provider_name,
                    model=model,
                    token_count=chunk.token_count or count_tokens(chunk.text, model),
                    metadata=dict(chunk.metadata),
                )
            )

        _log.info(
            "embed_complete",
            embedded=len(embedded),
            skipped=len(valid_chunks) - len(embedded),
        )
        return embedded

    # ── Cache management ──────────────────────────────────────────────────────

    def clear_cache(self) -> None:
        """Evict all cached vectors."""
        self._cache.clear()

    @property
    def cache_size(self) -> int:
        """Number of vectors currently in the cache."""
        return len(self._cache)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _make_batches(items: list, batch_size: int) -> list[list]:
    """Split *items* into sublists of at most *batch_size* items."""
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def _validate_vector(vec: list[float], expected_dims: int) -> bool:
    """Return True if *vec* looks like a valid embedding vector."""
    if not vec:
        return False
    if len(vec) != expected_dims:
        return False
    # Check for NaN / inf
    for v in vec:
        if not math.isfinite(v):
            return False
    return True
