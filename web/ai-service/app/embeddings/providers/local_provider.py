"""Local (deterministic) embedding provider — no API key required.

Generates deterministic pseudo-random unit vectors from SHA-256 hashes.
Used for:
  * Development without an OpenAI key.
  * Unit and integration tests (fast, offline, reproducible).
  * CI/CD pipelines.

The vectors are semantically meaningless but structurally correct:
  * Always ``dimensions`` floats.
  * Always normalised to unit length.
  * Same text → same vector across runs and processes.
"""
from __future__ import annotations

import hashlib
import math
import struct

from app.embeddings.providers.base_provider import BaseEmbeddingProvider

_DEFAULT_DIMENSIONS = 1536


class LocalProvider(BaseEmbeddingProvider):
    """Deterministic hash-based embedding provider.

    Args:
        dimensions: Length of each output vector. Default 1536.
        model: Model name stored on EmbeddedChunk. Default ``local-hash-v1``.
    """

    def __init__(
        self,
        dimensions: int = _DEFAULT_DIMENSIONS,
        model: str = "local-hash-v1",
    ) -> None:
        self._dimensions = dimensions
        self._model = model

    # ── BaseEmbeddingProvider ─────────────────────────────────────────────────

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return deterministic unit vectors — one per text."""
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


# ── Vector generation ─────────────────────────────────────────────────────────

def _deterministic_vector(text: str, dimensions: int) -> list[float]:
    """Generate a normalised unit vector deterministically from *text*.

    Algorithm:
      1. SHA-256(text) → 32-byte seed.
      2. Repeatedly SHA-256(seed || counter) to expand to ``dimensions × 4`` bytes.
      3. Unpack as big-endian unsigned ints, map to [-1, 1].
      4. L2-normalise.
    """
    seed = hashlib.sha256(text.encode("utf-8")).digest()

    # Expand seed to enough bytes
    raw = bytearray()
    counter = 0
    needed = dimensions * 4
    while len(raw) < needed:
        raw.extend(
            hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        )
        counter += 1

    # Unpack to floats in [-1, 1]
    vals: list[float] = []
    for i in range(dimensions):
        (n,) = struct.unpack_from(">I", raw, i * 4)
        vals.append((n / 4_294_967_295.0) * 2.0 - 1.0)

    # L2 normalise
    norm = math.sqrt(sum(v * v for v in vals))
    if norm > 0.0:
        vals = [v / norm for v in vals]

    return vals
