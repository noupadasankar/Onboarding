"""Local embedding provider.

Uses chromadb's bundled all-MiniLM-L6-v2 ONNX model for real semantic
embeddings (384-dim).  Falls back to deterministic hash-based vectors if
the ONNX runtime is not available — useful in minimal CI environments where
chromadb is installed without the onnxruntime extra.

The semantic model is downloaded once to ~/.cache/chroma/onnx_models/ by the
chromadb package; no separate installation is required.
"""
from __future__ import annotations

import hashlib
import math
import struct

from app.core.logging import get_logger

_log = get_logger()
_DEFAULT_DIMENSIONS = 384
_HASH_DIMENSIONS = 1536


def _try_build_onnx_fn():
    """Return chromadb's DefaultEmbeddingFunction or None if unavailable."""
    try:
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction  # type: ignore
        fn = DefaultEmbeddingFunction()
        # Warm up to confirm ONNX runtime works
        fn(["test"])
        _log.info("local_provider_onnx_ready", model="all-MiniLM-L6-v2", dimensions=384)
        return fn
    except Exception as exc:
        _log.warning("local_provider_onnx_unavailable", error=str(exc), fallback="hash-v1")
        return None


_ONNX_FN = _try_build_onnx_fn()

from app.embeddings.providers.base_provider import BaseEmbeddingProvider


class LocalProvider(BaseEmbeddingProvider):
    """Local embedding provider.

    Uses chromadb's all-MiniLM-L6-v2 ONNX model (384-dim) when available,
    otherwise falls back to deterministic hash vectors (1536-dim).

    Args:
        dimensions: Overrides the output dimension (only applies to hash fallback).
        model: Model name stored on EmbeddedChunk.
    """

    def __init__(
        self,
        dimensions: int | None = None,
        model: str | None = None,
    ) -> None:
        self._use_onnx = _ONNX_FN is not None
        if self._use_onnx:
            self._dimensions = _DEFAULT_DIMENSIONS
            self._model = model or "all-MiniLM-L6-v2"
        else:
            self._dimensions = dimensions or _HASH_DIMENSIONS
            self._model = model or "local-hash-v1"

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if self._use_onnx:
            result = _ONNX_FN(texts)
            return [list(map(float, vec)) for vec in result]
        return [_deterministic_vector(t, self._dimensions) for t in texts]

    @property
    def provider_name(self) -> str:
        return "local"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions


def _deterministic_vector(text: str, dimensions: int) -> list[float]:
    """Generate a normalised unit vector deterministically from *text* (fallback only)."""
    seed = hashlib.sha256(text.encode("utf-8")).digest()

    raw = bytearray()
    counter = 0
    needed = dimensions * 4
    while len(raw) < needed:
        raw.extend(hashlib.sha256(seed + counter.to_bytes(4, "big")).digest())
        counter += 1

    vals: list[float] = []
    for i in range(dimensions):
        (n,) = struct.unpack_from(">I", raw, i * 4)
        vals.append((n / 4_294_967_295.0) * 2.0 - 1.0)

    norm = math.sqrt(sum(v * v for v in vals))
    if norm > 0.0:
        vals = [v / norm for v in vals]

    return vals
