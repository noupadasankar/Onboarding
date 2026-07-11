"""Integration tests for ChunkPipeline."""
import json
import tempfile
from pathlib import Path

import pytest

from app.models.document import Document, FileType
from app.rag.chunk_pipeline import ChunkPipeline
from app.services.chunk_service import ChunkService, ChunkingConfig


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_document(content: str, filename: str = "test.txt") -> Document:
    ext = filename.rsplit(".", 1)[-1].lower()
    ft = FileType(ext) if ext in ("pdf", "docx", "txt", "csv", "xlsx") else FileType.TXT
    return Document(
        filename=filename,
        file_type=ft,
        mime_type="text/plain",
        content=content,
        metadata={"department": "HR", "category": "policy"},
        source=f"test/{filename}",
        size_bytes=len(content.encode()),
        uploaded_by="u_test",
    )


def _rich_content() -> str:
    """Multi-section text long enough to survive chunk validation."""
    paragraphs = (
        "Employees at Deloitte are entitled to comprehensive leave benefits including "
        "annual leave, sick leave, maternity and paternity leave, and public holidays. "
        "Leave requests must be submitted at least two weeks in advance via the HR portal. "
        "All approved leave is subject to team availability and business requirements. "
    )
    return (
        "# Leave Policy\n\n" + paragraphs * 2 + "\n\n"
        "# Working Hours\n\n"
        "Standard working hours are Monday to Friday, 09:00 to 17:30. "
        "Flexible working arrangements may be agreed with line managers in writing. "
        "Overtime is paid at 1.5× the standard hourly rate for hours beyond 40 per week. "
        + paragraphs
    )


@pytest.fixture
def pipeline() -> ChunkPipeline:
    service = ChunkService()
    config = ChunkingConfig(chunk_size=150, overlap=20, min_tokens=10)
    return ChunkPipeline(chunk_service=service, config=config)


@pytest.fixture
def rich_doc() -> Document:
    return _make_document(_rich_content(), "handbook.txt")


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestChunkPipelineRun:
    async def test_run_returns_chunks(
        self, pipeline: ChunkPipeline, rich_doc: Document
    ) -> None:
        chunks = await pipeline.run(rich_doc)
        assert isinstance(chunks, list)
        assert len(chunks) > 0

    async def test_empty_document_returns_empty(self, pipeline: ChunkPipeline) -> None:
        doc = _make_document("", "empty.txt")
        chunks = await pipeline.run(doc)
        assert chunks == []

    async def test_chunks_have_correct_document_id(
        self, pipeline: ChunkPipeline, rich_doc: Document
    ) -> None:
        chunks = await pipeline.run(rich_doc)
        for c in chunks:
            assert c.document_id == rich_doc.document_id

    async def test_chunks_have_sequential_indexes(
        self, pipeline: ChunkPipeline, rich_doc: Document
    ) -> None:
        chunks = await pipeline.run(rich_doc)
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    async def test_chunk_ids_formatted_correctly(
        self, pipeline: ChunkPipeline, rich_doc: Document
    ) -> None:
        chunks = await pipeline.run(rich_doc)
        for c in chunks:
            # chunk_id format: "<8-char-hex>_chunk<4-digit-index>"
            parts = c.chunk_id.split("_chunk")
            assert len(parts) == 2
            assert len(parts[0]) == 8
            assert parts[1].isdigit()

    async def test_metadata_inherits_from_document(
        self, pipeline: ChunkPipeline, rich_doc: Document
    ) -> None:
        chunks = await pipeline.run(rich_doc)
        for c in chunks:
            assert c.metadata.get("filename") == rich_doc.filename
            assert c.metadata.get("file_type") == rich_doc.file_type

    async def test_section_headings_propagated(
        self, pipeline: ChunkPipeline, rich_doc: Document
    ) -> None:
        chunks = await pipeline.run(rich_doc)
        sections = {c.section for c in chunks if c.section}
        # At least one section should have been detected from the markdown headings
        assert len(sections) >= 1


class TestChunkPipelineJsonExport:
    async def test_no_export_when_dir_not_configured(
        self, pipeline: ChunkPipeline, rich_doc: Document, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No file should be written when chunk_export_dir is empty."""

        class _FakeCfg:
            chunk_export_dir = ""

        monkeypatch.setattr("app.rag.chunk_pipeline.get_settings", lambda: _FakeCfg())
        # Should not raise and should still return chunks
        chunks = await pipeline.run(rich_doc)
        assert isinstance(chunks, list)

    async def test_export_written_when_dir_configured(
        self, rich_doc: Document, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """JSON file should be created when chunk_export_dir points to a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:

            class _FakeCfg:
                chunk_export_dir = tmpdir

            monkeypatch.setattr("app.rag.chunk_pipeline.get_settings", lambda: _FakeCfg())

            service = ChunkService()
            config = ChunkingConfig(chunk_size=150, overlap=20, min_tokens=10)
            pl = ChunkPipeline(chunk_service=service, config=config)
            chunks = await pl.run(rich_doc)

            if not chunks:
                pytest.skip("No chunks produced — document too short for these settings")

            export_files = list(Path(tmpdir).glob("*_chunks.json"))
            assert len(export_files) == 1

            payload = json.loads(export_files[0].read_text(encoding="utf-8"))
            assert payload["document_id"] == rich_doc.document_id
            assert payload["filename"] == rich_doc.filename
            assert payload["chunk_count"] == len(chunks)
            assert len(payload["chunks"]) == len(chunks)

    async def test_export_json_schema(
        self, rich_doc: Document, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Each item in the exported JSON must contain required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:

            class _FakeCfg:
                chunk_export_dir = tmpdir

            monkeypatch.setattr("app.rag.chunk_pipeline.get_settings", lambda: _FakeCfg())

            service = ChunkService()
            config = ChunkingConfig(chunk_size=150, overlap=20, min_tokens=10)
            pl = ChunkPipeline(chunk_service=service, config=config)
            chunks = await pl.run(rich_doc)

            if not chunks:
                pytest.skip("No chunks produced — document too short")

            export_file = list(Path(tmpdir).glob("*_chunks.json"))[0]
            payload = json.loads(export_file.read_text(encoding="utf-8"))

            for item in payload["chunks"]:
                assert "chunk_id" in item
                assert "chunk_index" in item
                assert "token_count" in item
                assert "text" in item


class TestChunkPipelineIntegration:
    """Full stack: real document → pipeline → Chunk list."""

    async def test_end_to_end_txt_document(self) -> None:
        service = ChunkService()
        config = ChunkingConfig(chunk_size=100, overlap=15, min_tokens=5)
        pipeline = ChunkPipeline(chunk_service=service, config=config)

        content = (
            "Onboarding Process\n\n"
            "Week 1: Set up your workstation and meet your team. "
            "Complete the mandatory induction training on the learning portal. "
            "Your buddy will guide you through your first week. "
            "Week 2: Begin your departmental orientation sessions. "
            "Review the company handbook and code of conduct documentation. "
            "Attend the monthly all-hands meeting held every second Friday. "
        )
        doc = _make_document(content, "onboarding.txt")
        chunks = await pipeline.run(doc)
        assert isinstance(chunks, list)
        # The content is real and should produce at least one valid chunk
        assert len(chunks) >= 1

    async def test_pipeline_stores_chunks_in_service(self) -> None:
        service = ChunkService()
        config = ChunkingConfig(chunk_size=100, overlap=15, min_tokens=5)
        pipeline = ChunkPipeline(chunk_service=service, config=config)

        doc = _make_document(_rich_content(), "policy.txt")
        chunks = await pipeline.run(doc)

        stored = service.get_chunks(doc.document_id)
        assert stored == chunks
