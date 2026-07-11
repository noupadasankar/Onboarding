"""Tests for ChunkService — chunking pipeline orchestrator."""
import pytest

from app.models.chunk import Chunk
from app.models.document import Document, FileType
from app.services.chunk_service import ChunkService, ChunkingConfig


# ── Shared helpers ────────────────────────────────────────────────────────────

def _make_document(content: str, filename: str = "handbook.txt") -> Document:
    """Build a minimal Document for testing."""
    ext = filename.rsplit(".", 1)[-1].lower()
    file_type = FileType(ext) if ext in ("pdf", "docx", "txt", "csv", "xlsx") else FileType.TXT
    return Document(
        filename=filename,
        file_type=file_type,
        mime_type="text/plain",
        content=content,
        metadata={},
        source=f"test/{filename}",
        size_bytes=len(content.encode()),
        uploaded_by="u_test",
    )


def _long_content(sections: int = 4) -> str:
    """Generate realistic multi-section text long enough to produce valid chunks."""
    body = (
        "Employees are entitled to annual leave, sick leave, and public holidays. "
        "All requests must be submitted via the HR portal at least two weeks in advance. "
        "Management reserves the right to refuse requests during peak periods. "
        "Unused leave may be carried over to the following year subject to approval. "
    )
    text = ""
    headings = ["Leave Policy", "Working Hours", "Code of Conduct", "Benefits"]
    for i in range(sections):
        heading = headings[i % len(headings)]
        text += f"\n{heading}\n\n" + body * 3 + "\n"
    return text.strip()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def service() -> ChunkService:
    """Fresh ChunkService per test."""
    return ChunkService()


@pytest.fixture
def long_doc() -> Document:
    return _make_document(_long_content(), "handbook.txt")


@pytest.fixture
def relaxed_config() -> ChunkingConfig:
    """Lower thresholds so short test texts still produce chunks."""
    return ChunkingConfig(chunk_size=100, overlap=20, min_tokens=5)


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestProcess:
    async def test_returns_list_of_chunks(
        self, service: ChunkService, long_doc: Document, relaxed_config: ChunkingConfig
    ) -> None:
        chunks = await service.process(long_doc, relaxed_config)
        assert isinstance(chunks, list)
        assert len(chunks) > 0

    async def test_chunks_are_chunk_instances(
        self, service: ChunkService, long_doc: Document, relaxed_config: ChunkingConfig
    ) -> None:
        chunks = await service.process(long_doc, relaxed_config)
        assert all(isinstance(c, Chunk) for c in chunks)

    async def test_empty_document_returns_empty_list(
        self, service: ChunkService
    ) -> None:
        doc = _make_document("", "empty.txt")
        chunks = await service.process(doc)
        assert chunks == []

    async def test_whitespace_only_document_returns_empty_list(
        self, service: ChunkService
    ) -> None:
        doc = _make_document("   \n\n\t  ", "blank.txt")
        chunks = await service.process(doc)
        assert chunks == []

    async def test_chunk_ids_are_unique(
        self, service: ChunkService, long_doc: Document, relaxed_config: ChunkingConfig
    ) -> None:
        chunks = await service.process(long_doc, relaxed_config)
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    async def test_chunk_indexes_are_sequential(
        self, service: ChunkService, long_doc: Document, relaxed_config: ChunkingConfig
    ) -> None:
        chunks = await service.process(long_doc, relaxed_config)
        indexes = [c.chunk_index for c in chunks]
        assert indexes == list(range(len(chunks)))

    async def test_chunk_document_id_matches_document(
        self, service: ChunkService, long_doc: Document, relaxed_config: ChunkingConfig
    ) -> None:
        chunks = await service.process(long_doc, relaxed_config)
        for c in chunks:
            assert c.document_id == long_doc.document_id

    async def test_metadata_inherits_filename(
        self, service: ChunkService, long_doc: Document, relaxed_config: ChunkingConfig
    ) -> None:
        chunks = await service.process(long_doc, relaxed_config)
        for c in chunks:
            assert c.metadata.get("filename") == long_doc.filename

    async def test_default_config_used_when_none_given(
        self, service: ChunkService, long_doc: Document
    ) -> None:
        # Default min_tokens=50 means a rich document should still yield chunks
        chunks = await service.process(long_doc)
        assert isinstance(chunks, list)

    async def test_chunk_text_non_empty(
        self, service: ChunkService, long_doc: Document, relaxed_config: ChunkingConfig
    ) -> None:
        chunks = await service.process(long_doc, relaxed_config)
        for c in chunks:
            assert c.text.strip()

    async def test_chunk_token_count_positive(
        self, service: ChunkService, long_doc: Document, relaxed_config: ChunkingConfig
    ) -> None:
        chunks = await service.process(long_doc, relaxed_config)
        for c in chunks:
            assert c.token_count > 0

    async def test_reprocess_overwrites_existing_chunks(
        self, service: ChunkService, long_doc: Document, relaxed_config: ChunkingConfig
    ) -> None:
        chunks_first = await service.process(long_doc, relaxed_config)
        chunks_second = await service.process(long_doc, relaxed_config)
        # Store should be replaced, not appended
        assert len(service.get_chunks(long_doc.document_id)) == len(chunks_second)
        assert len(chunks_first) == len(chunks_second)


class TestGetChunks:
    async def test_get_chunks_returns_processed_chunks(
        self, service: ChunkService, long_doc: Document, relaxed_config: ChunkingConfig
    ) -> None:
        expected = await service.process(long_doc, relaxed_config)
        result = service.get_chunks(long_doc.document_id)
        assert result == expected

    def test_get_chunks_unprocessed_returns_empty(
        self, service: ChunkService
    ) -> None:
        assert service.get_chunks("nonexistent-id") == []


class TestHasChunks:
    async def test_has_chunks_true_after_processing(
        self, service: ChunkService, long_doc: Document, relaxed_config: ChunkingConfig
    ) -> None:
        await service.process(long_doc, relaxed_config)
        assert service.has_chunks(long_doc.document_id)

    def test_has_chunks_false_before_processing(
        self, service: ChunkService
    ) -> None:
        assert not service.has_chunks("nonexistent-id")

    async def test_has_chunks_false_after_delete(
        self, service: ChunkService, long_doc: Document, relaxed_config: ChunkingConfig
    ) -> None:
        await service.process(long_doc, relaxed_config)
        service.delete_chunks(long_doc.document_id)
        assert not service.has_chunks(long_doc.document_id)


class TestDeleteChunks:
    async def test_delete_returns_chunk_count(
        self, service: ChunkService, long_doc: Document, relaxed_config: ChunkingConfig
    ) -> None:
        chunks = await service.process(long_doc, relaxed_config)
        count = service.delete_chunks(long_doc.document_id)
        assert count == len(chunks)

    def test_delete_nonexistent_returns_zero(self, service: ChunkService) -> None:
        assert service.delete_chunks("nonexistent-id") == 0

    async def test_delete_removes_from_store(
        self, service: ChunkService, long_doc: Document, relaxed_config: ChunkingConfig
    ) -> None:
        await service.process(long_doc, relaxed_config)
        service.delete_chunks(long_doc.document_id)
        assert service.get_chunks(long_doc.document_id) == []


class TestListProcessed:
    async def test_lists_processed_document_ids(
        self, service: ChunkService, relaxed_config: ChunkingConfig
    ) -> None:
        doc_a = _make_document(_long_content(), "doc_a.txt")
        doc_b = _make_document(_long_content(), "doc_b.txt")
        await service.process(doc_a, relaxed_config)
        await service.process(doc_b, relaxed_config)
        processed = service.list_processed()
        assert doc_a.document_id in processed
        assert doc_b.document_id in processed

    def test_empty_service_returns_empty_list(self, service: ChunkService) -> None:
        assert service.list_processed() == []
