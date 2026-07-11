"""Tests for EmbeddingService — batching, validation, cache, skipping."""
import math
from unittest.mock import AsyncMock

import pytest

from app.embeddings.embedding_service import EmbeddingConfig, EmbeddingService, _make_batches, _validate_vector
from app.embeddings.providers.local_provider import LocalProvider
from app.models.chunk import Chunk
from app.models.document import FileType


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_chunk(text: str, token_count: int = 100, idx: int = 0) -> Chunk:
    doc_id = "00000000-0000-0000-0000-000000000001"
    return Chunk(
        chunk_id=Chunk.build_id(doc_id, idx),
        document_id=doc_id,
        chunk_index=idx,
        text=text,
        token_count=token_count,
        metadata={"filename": "test.txt", "file_type": FileType.TXT},
    )


def _make_chunks(n: int, text_prefix: str = "Content block") -> list[Chunk]:
    return [_make_chunk(f"{text_prefix} {i}. " * 10, idx=i) for i in range(n)]


@pytest.fixture
def local_service() -> EmbeddingService:
    return EmbeddingService(LocalProvider(dimensions=64))


# ── embed_chunks ───────────────────────────────────────────────────────────────

class TestEmbedChunks:
    async def test_returns_embedded_chunk_per_valid_chunk(
        self, local_service: EmbeddingService
    ) -> None:
        chunks = _make_chunks(3)
        result = await local_service.embed_chunks(chunks)
        assert len(result) == 3

    async def test_empty_input_returns_empty(
        self, local_service: EmbeddingService
    ) -> None:
        result = await local_service.embed_chunks([])
        assert result == []

    async def test_embedded_chunk_ids_match_chunk_ids(
        self, local_service: EmbeddingService
    ) -> None:
        chunks = _make_chunks(3)
        result = await local_service.embed_chunks(chunks)
        for ec, c in zip(result, chunks):
            assert ec.chunk_id == c.chunk_id

    async def test_embedding_length_matches_provider_dimensions(
        self, local_service: EmbeddingService
    ) -> None:
        chunks = _make_chunks(2)
        result = await local_service.embed_chunks(chunks)
        for ec in result:
            assert ec.dimensions == 64
            assert len(ec.embedding) == 64

    async def test_provider_name_on_embedded_chunk(
        self, local_service: EmbeddingService
    ) -> None:
        chunks = _make_chunks(1)
        result = await local_service.embed_chunks(chunks)
        assert result[0].provider == "local"

    async def test_model_name_on_embedded_chunk(
        self, local_service: EmbeddingService
    ) -> None:
        chunks = _make_chunks(1)
        result = await local_service.embed_chunks(chunks)
        assert result[0].model == "local-hash-v1"

    async def test_empty_text_chunk_skipped(
        self, local_service: EmbeddingService
    ) -> None:
        chunks = [
            _make_chunk("", token_count=0, idx=0),
            _make_chunk("valid content here " * 5, token_count=50, idx=1),
        ]
        result = await local_service.embed_chunks(chunks)
        assert len(result) == 1

    async def test_whitespace_only_chunk_skipped(
        self, local_service: EmbeddingService
    ) -> None:
        chunks = [
            _make_chunk("   \n\t  ", token_count=0, idx=0),
            _make_chunk("good content " * 5, token_count=50, idx=1),
        ]
        result = await local_service.embed_chunks(chunks)
        assert len(result) == 1

    async def test_metadata_inherited(
        self, local_service: EmbeddingService
    ) -> None:
        chunk = _make_chunk("some text " * 5)
        chunk.metadata["section"] = "Leave Policy"
        result = await local_service.embed_chunks([chunk])
        assert result[0].metadata.get("section") == "Leave Policy"

    async def test_document_id_propagated(
        self, local_service: EmbeddingService
    ) -> None:
        chunk = _make_chunk("text " * 10)
        result = await local_service.embed_chunks([chunk])
        assert result[0].document_id == chunk.document_id

    async def test_all_floats_finite(
        self, local_service: EmbeddingService
    ) -> None:
        chunks = _make_chunks(2)
        result = await local_service.embed_chunks(chunks)
        for ec in result:
            assert all(math.isfinite(v) for v in ec.embedding)


class TestEmbeddingBatching:
    async def test_large_batch_processed(self) -> None:
        provider = LocalProvider(dimensions=16)
        service = EmbeddingService(provider)
        chunks = _make_chunks(250)
        result = await service.embed_chunks(
            chunks, EmbeddingConfig(batch_size=100)
        )
        assert len(result) == 250

    async def test_batch_size_one_works(self) -> None:
        provider = LocalProvider(dimensions=16)
        service = EmbeddingService(provider)
        chunks = _make_chunks(5)
        result = await service.embed_chunks(
            chunks, EmbeddingConfig(batch_size=1)
        )
        assert len(result) == 5

    async def test_provider_called_correct_times(self) -> None:
        """With batch_size=3 and 7 chunks, the provider should be called 3 times."""
        provider = LocalProvider(dimensions=16)
        original_embed = provider.embed_batch
        call_count = 0

        async def counting_embed(texts: list[str]) -> list[list[float]]:
            nonlocal call_count
            call_count += 1
            return await original_embed(texts)

        provider.embed_batch = counting_embed  # type: ignore[method-assign]
        service = EmbeddingService(provider)
        await service.embed_chunks(_make_chunks(7), EmbeddingConfig(batch_size=3))
        assert call_count == 3  # ceil(7 / 3) = 3


class TestEmbeddingCache:
    async def test_cache_hit_avoids_second_provider_call(self) -> None:
        provider = LocalProvider(dimensions=16)
        call_count = 0
        original = provider.embed_batch

        async def counting(texts: list[str]) -> list[list[float]]:
            nonlocal call_count
            call_count += 1
            return await original(texts)

        provider.embed_batch = counting  # type: ignore[method-assign]
        service = EmbeddingService(provider)
        chunk = _make_chunk("unique content " * 10)

        await service.embed_chunks([chunk], EmbeddingConfig(enable_cache=True))
        await service.embed_chunks([chunk], EmbeddingConfig(enable_cache=True))
        # Second call should be served from cache — provider not called again
        assert call_count == 1

    async def test_cache_disabled_calls_provider_twice(self) -> None:
        provider = LocalProvider(dimensions=16)
        call_count = 0
        original = provider.embed_batch

        async def counting(texts: list[str]) -> list[list[float]]:
            nonlocal call_count
            call_count += 1
            return await original(texts)

        provider.embed_batch = counting  # type: ignore[method-assign]
        service = EmbeddingService(provider)
        chunk = _make_chunk("unique content " * 10)

        await service.embed_chunks([chunk], EmbeddingConfig(enable_cache=False))
        await service.embed_chunks([chunk], EmbeddingConfig(enable_cache=False))
        assert call_count == 2

    async def test_clear_cache(self) -> None:
        service = EmbeddingService(LocalProvider(dimensions=16))
        chunks = _make_chunks(3)
        await service.embed_chunks(chunks, EmbeddingConfig(enable_cache=True))
        assert service.cache_size == 3
        service.clear_cache()
        assert service.cache_size == 0


# ── Validation helpers ────────────────────────────────────────────────────────

class TestValidateVector:
    def test_valid_vector(self) -> None:
        vec = [0.1, -0.2, 0.3, 0.4]
        assert _validate_vector(vec, 4)

    def test_empty_vector_invalid(self) -> None:
        assert not _validate_vector([], 4)

    def test_wrong_dimensions_invalid(self) -> None:
        assert not _validate_vector([0.1, 0.2], 4)

    def test_nan_invalid(self) -> None:
        assert not _validate_vector([0.1, float("nan"), 0.3, 0.4], 4)

    def test_inf_invalid(self) -> None:
        assert not _validate_vector([0.1, float("inf"), 0.3, 0.4], 4)


class TestMakeBatches:
    def test_even_split(self) -> None:
        assert _make_batches(list(range(9)), 3) == [
            [0, 1, 2], [3, 4, 5], [6, 7, 8]
        ]

    def test_uneven_split(self) -> None:
        batches = _make_batches(list(range(5)), 3)
        assert len(batches) == 2
        assert len(batches[0]) == 3
        assert len(batches[1]) == 2

    def test_single_item(self) -> None:
        assert _make_batches(["x"], 10) == [["x"]]

    def test_empty_list(self) -> None:
        assert _make_batches([], 10) == []
