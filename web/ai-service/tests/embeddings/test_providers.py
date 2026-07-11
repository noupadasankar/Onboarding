"""Tests for the embedding providers sub-package."""
import math

import pytest

from app.embeddings.providers.base_provider import BaseEmbeddingProvider, EmbeddingProviderError
from app.embeddings.providers.local_provider import LocalProvider, _deterministic_vector


# ── LocalProvider ──────────────────────────────────────────────────────────────

class TestLocalProviderProperties:
    def test_provider_name(self) -> None:
        assert LocalProvider().provider_name == "local"

    def test_default_model_name(self) -> None:
        assert LocalProvider().model_name == "local-hash-v1"

    def test_custom_model_name(self) -> None:
        p = LocalProvider(model="my-model")
        assert p.model_name == "my-model"

    def test_default_dimensions(self) -> None:
        assert LocalProvider().dimensions == 1536

    def test_custom_dimensions(self) -> None:
        assert LocalProvider(dimensions=768).dimensions == 768


class TestLocalProviderEmbedBatch:
    async def test_returns_one_vector_per_text(self) -> None:
        p = LocalProvider(dimensions=64)
        vecs = await p.embed_batch(["hello", "world"])
        assert len(vecs) == 2

    async def test_vector_length_matches_dimensions(self) -> None:
        p = LocalProvider(dimensions=64)
        vecs = await p.embed_batch(["test text"])
        assert len(vecs[0]) == 64

    async def test_deterministic_same_text(self) -> None:
        p = LocalProvider(dimensions=64)
        v1 = await p.embed_batch(["same text"])
        v2 = await p.embed_batch(["same text"])
        assert v1 == v2

    async def test_different_text_different_vector(self) -> None:
        p = LocalProvider(dimensions=64)
        vecs = await p.embed_batch(["text A", "text B"])
        assert vecs[0] != vecs[1]

    async def test_all_floats(self) -> None:
        p = LocalProvider(dimensions=32)
        vecs = await p.embed_batch(["float check"])
        assert all(isinstance(v, float) for v in vecs[0])

    async def test_unit_normalised(self) -> None:
        p = LocalProvider(dimensions=64)
        vecs = await p.embed_batch(["normalised vector"])
        vec = vecs[0]
        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 1e-6

    async def test_large_batch(self) -> None:
        p = LocalProvider(dimensions=16)
        texts = [f"text {i}" for i in range(200)]
        vecs = await p.embed_batch(texts)
        assert len(vecs) == 200

    async def test_empty_string_embeds(self) -> None:
        p = LocalProvider(dimensions=16)
        vecs = await p.embed_batch([""])
        assert len(vecs) == 1
        assert len(vecs[0]) == 16


class TestDeterministicVector:
    def test_output_length(self) -> None:
        v = _deterministic_vector("hello", 64)
        assert len(v) == 64

    def test_unit_norm(self) -> None:
        v = _deterministic_vector("hello world", 32)
        norm = math.sqrt(sum(x * x for x in v))
        assert abs(norm - 1.0) < 1e-6

    def test_reproducible(self) -> None:
        v1 = _deterministic_vector("optiagent", 32)
        v2 = _deterministic_vector("optiagent", 32)
        assert v1 == v2

    def test_values_in_range(self) -> None:
        v = _deterministic_vector("range check", 128)
        # After normalisation floats should be in (-1, 1)
        assert all(-1.0 <= x <= 1.0 for x in v)


class TestBaseProviderInterface:
    def test_subclass_must_implement_embed_batch(self) -> None:
        class BadProvider(BaseEmbeddingProvider):
            @property
            def provider_name(self) -> str:
                return "bad"
            @property
            def model_name(self) -> str:
                return "bad-model"
            @property
            def dimensions(self) -> int:
                return 1

        with pytest.raises(TypeError):
            BadProvider()  # type: ignore[abstract]

    def test_provider_error_is_runtime_error(self) -> None:
        exc = EmbeddingProviderError("test error")
        assert isinstance(exc, RuntimeError)
        assert str(exc) == "test error"
