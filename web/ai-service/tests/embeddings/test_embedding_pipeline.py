"""Integration tests for EmbeddingPipeline — Chunk → EmbeddedChunk end-to-end."""
import json
import tempfile
from pathlib import Path

import pytest

from app.embeddings.embedding_pipeline import EmbeddingPipeline
from app.embeddings.embedding_service import EmbeddingConfig
from app.embeddings.providers.local_provider import LocalProvider
from app.models.chunk import Chunk
from app.models.document import FileType


# ── Helpers ───────────────────────────────────────────────────────────────────

def _doc_id() -> str:
    return "aaaabbbb-cccc-dddd-eeee-ffffffffffff"


def _make_chunk(text: str, idx: int = 0) -> Chunk:
    doc_id = _doc_id()
    return Chunk(
        chunk_id=Chunk.build_id(doc_id, idx),
        document_id=doc_id,
        chunk_index=idx,
        text=text,
        token_count=len(text.split()),
        metadata={"filename": "handbook.txt", "file_type": FileType.TXT},
    )


def _make_chunks(n: int) -> list[Chunk]:
    return [_make_chunk(f"Content for chunk {i}. " * 8, idx=i) for i in range(n)]


@pytest.fixture
def pipeline() -> EmbeddingPipeline:
    return EmbeddingPipeline(
        provider=LocalProvider(dimensions=32),
        config=EmbeddingConfig(batch_size=10),
    )


# ── Pipeline run tests ────────────────────────────────────────────────────────

class TestEmbeddingPipelineRun:
    async def test_returns_embedded_chunks(self, pipeline: EmbeddingPipeline) -> None:
        chunks = _make_chunks(5)
        result = await pipeline.run(chunks, "handbook.txt")
        assert len(result) == 5

    async def test_empty_chunks_returns_empty(self, pipeline: EmbeddingPipeline) -> None:
        result = await pipeline.run([], "handbook.txt")
        assert result == []

    async def test_each_result_has_embedding(self, pipeline: EmbeddingPipeline) -> None:
        chunks = _make_chunks(3)
        result = await pipeline.run(chunks)
        for ec in result:
            assert len(ec.embedding) == 32

    async def test_chunk_ids_preserved(self, pipeline: EmbeddingPipeline) -> None:
        chunks = _make_chunks(4)
        result = await pipeline.run(chunks)
        for ec, c in zip(result, chunks):
            assert ec.chunk_id == c.chunk_id

    async def test_document_ids_preserved(self, pipeline: EmbeddingPipeline) -> None:
        chunks = _make_chunks(3)
        result = await pipeline.run(chunks)
        for ec in result:
            assert ec.document_id == _doc_id()


class TestEmbeddingPipelineJsonExport:
    async def test_export_written_when_dir_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            class _FakeCfg:
                embedding_export_dir = tmpdir

            monkeypatch.setattr(
                "app.embeddings.embedding_pipeline.get_settings",
                lambda: _FakeCfg(),
            )
            pl = EmbeddingPipeline(
                provider=LocalProvider(dimensions=16),
                config=EmbeddingConfig(batch_size=5),
            )
            chunks = _make_chunks(3)
            await pl.run(chunks, "handbook.txt")

            files = list(Path(tmpdir).glob("*_embeddings.json"))
            assert len(files) == 1

    async def test_export_schema(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            class _FakeCfg:
                embedding_export_dir = tmpdir

            monkeypatch.setattr(
                "app.embeddings.embedding_pipeline.get_settings",
                lambda: _FakeCfg(),
            )
            pl = EmbeddingPipeline(
                provider=LocalProvider(dimensions=16),
                config=EmbeddingConfig(),
            )
            chunks = _make_chunks(2)
            result = await pl.run(chunks, "handbook.txt")

            export = json.loads(
                list(Path(tmpdir).glob("*_embeddings.json"))[0].read_text("utf-8")
            )
            assert export["embedding_count"] == len(result)
            assert "exported_at" in export
            assert "model" in export
            assert "dimensions" in export
            for item in export["embeddings"]:
                assert "chunk_id" in item
                assert "embedding" in item
                assert "dimensions" in item

    async def test_no_export_when_dir_not_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _FakeCfg:
            embedding_export_dir = ""

        monkeypatch.setattr(
            "app.embeddings.embedding_pipeline.get_settings",
            lambda: _FakeCfg(),
        )
        pl = EmbeddingPipeline(provider=LocalProvider(dimensions=16))
        chunks = _make_chunks(2)
        result = await pl.run(chunks, "handbook.txt")
        assert len(result) == 2  # no crash, no file written


class TestEmbeddingPipelineIntegration:
    """Full stack via factory — uses 'local' provider from default settings."""

    async def test_factory_creates_local_pipeline(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _FakeCfg:
            embedding_provider = "local"
            embedding_export_dir = ""

        monkeypatch.setattr(
            "app.embeddings.embedding_factory.get_settings",
            lambda: _FakeCfg(),
        )
        monkeypatch.setattr(
            "app.embeddings.embedding_pipeline.get_settings",
            lambda: _FakeCfg(),
        )

        pl = EmbeddingPipeline()  # no provider_name → reads settings
        chunks = _make_chunks(3)
        result = await pl.run(chunks)
        assert len(result) == 3
        assert result[0].provider == "local"
