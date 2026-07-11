"""Unit tests for DocumentService.

Each test uses a fresh DocumentService instance so state does not leak.
Fixture bytes come from tests/loaders/conftest.py (shared via conftest chain).
"""
import pytest
from fastapi import HTTPException

from app.services.document_service import DocumentService
from tests.loaders.conftest import make_text_pdf, make_docx, make_xlsx


@pytest.fixture
def service() -> DocumentService:
    return DocumentService()


@pytest.fixture
def sample_pdf() -> bytes:
    return make_text_pdf("HR Policy Document\nAll employees must follow company rules.")


@pytest.fixture
def sample_docx() -> bytes:
    return make_docx(["Leave Policy", "Employees are entitled to 20 days of annual leave."])


@pytest.fixture
def sample_csv() -> bytes:
    return b"name,role\nAlice,Manager\nBob,Developer\n"


@pytest.fixture
def sample_xlsx() -> bytes:
    return make_xlsx({"Sheet1": [["Col A", "Col B"], ["1", "2"]]})


class TestIngest:
    async def test_pdf_ingested(self, service: DocumentService, sample_pdf: bytes) -> None:
        doc = await service.ingest(sample_pdf, "policy.pdf", "u_test")
        assert doc.document_id
        assert doc.filename == "policy.pdf"
        assert doc.file_type.value == "pdf"
        assert doc.uploaded_by == "u_test"

    async def test_docx_ingested(self, service: DocumentService, sample_docx: bytes) -> None:
        doc = await service.ingest(sample_docx, "leave.docx", "u_test")
        assert doc.file_type.value == "docx"

    async def test_csv_ingested(self, service: DocumentService, sample_csv: bytes) -> None:
        doc = await service.ingest(sample_csv, "hr_data.csv", "u_test")
        assert doc.file_type.value == "csv"

    async def test_xlsx_ingested(self, service: DocumentService, sample_xlsx: bytes) -> None:
        doc = await service.ingest(sample_xlsx, "grades.xlsx", "u_test")
        assert doc.file_type.value == "xlsx"

    async def test_document_stored_after_ingest(
        self, service: DocumentService, sample_pdf: bytes
    ) -> None:
        doc = await service.ingest(sample_pdf, "policy.pdf", "u_test")
        fetched = service.get(doc.document_id)
        assert fetched.document_id == doc.document_id

    async def test_unsupported_type_raises_http_415(
        self, service: DocumentService
    ) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await service.ingest(b"data", "report.pptx", "u_test")
        assert exc_info.value.status_code == 415

    async def test_empty_file_raises_http_400(
        self, service: DocumentService
    ) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await service.ingest(b"", "empty.pdf", "u_test")
        assert exc_info.value.status_code == 400

    async def test_corrupted_pdf_raises_http_422(
        self, service: DocumentService
    ) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await service.ingest(b"%PDF-1.4 corrupted", "bad.pdf", "u_test")
        assert exc_info.value.status_code == 422


class TestCRUD:
    async def test_get_existing(self, service: DocumentService, sample_pdf: bytes) -> None:
        doc = await service.ingest(sample_pdf, "policy.pdf", "u_test")
        fetched = service.get(doc.document_id)
        assert fetched.document_id == doc.document_id

    def test_get_missing_raises_404(self, service: DocumentService) -> None:
        with pytest.raises(HTTPException) as exc_info:
            service.get("non-existent-id")
        assert exc_info.value.status_code == 404

    async def test_list_all_returns_ingested(
        self, service: DocumentService, sample_pdf: bytes, sample_csv: bytes
    ) -> None:
        await service.ingest(sample_pdf, "a.pdf", "u_test")
        await service.ingest(sample_csv, "b.csv", "u_test")
        docs = service.list_all()
        assert len(docs) == 2

    async def test_delete_removes_document(
        self, service: DocumentService, sample_pdf: bytes
    ) -> None:
        doc = await service.ingest(sample_pdf, "policy.pdf", "u_test")
        service.delete(doc.document_id)
        assert len(service.list_all()) == 0

    def test_delete_missing_raises_404(self, service: DocumentService) -> None:
        with pytest.raises(HTTPException) as exc_info:
            service.delete("non-existent-id")
        assert exc_info.value.status_code == 404
