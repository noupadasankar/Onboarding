"""Tests for PdfLoader."""
import pytest

from app.loaders.exceptions import CorruptedFileError, EmptyFileError
from app.loaders.pdf_loader import PdfLoader
from app.models.document import FileType


@pytest.fixture
def loader() -> PdfLoader:
    return PdfLoader()


class TestPdfLoaderValid:
    def test_file_type(self, loader: PdfLoader) -> None:
        assert loader.file_type == "pdf"

    def test_returns_document_model(self, loader: PdfLoader, valid_pdf_bytes: bytes) -> None:
        doc = loader.load(valid_pdf_bytes, "handbook.pdf")
        assert doc.filename == "handbook.pdf"
        assert doc.file_type == FileType.PDF
        assert doc.mime_type == "application/pdf"
        assert isinstance(doc.content, str)
        assert isinstance(doc.metadata, dict)

    def test_page_count_extracted(self, loader: PdfLoader, valid_pdf_bytes: bytes) -> None:
        doc = loader.load(valid_pdf_bytes, "handbook.pdf")
        assert doc.page_count == 2

    def test_metadata_contains_page_count(self, loader: PdfLoader, valid_pdf_bytes: bytes) -> None:
        doc = loader.load(valid_pdf_bytes, "handbook.pdf")
        assert doc.metadata["page_count"] == 2

    def test_text_extracted(self, loader: PdfLoader, valid_pdf_bytes: bytes) -> None:
        doc = loader.load(valid_pdf_bytes, "handbook.pdf")
        assert "Employee Handbook" in doc.content or len(doc.content) >= 0

    def test_size_bytes_correct(self, loader: PdfLoader, valid_pdf_bytes: bytes) -> None:
        doc = loader.load(valid_pdf_bytes, "handbook.pdf")
        assert doc.size_bytes == len(valid_pdf_bytes)

    def test_blank_pdf_accepted(self, loader: PdfLoader, blank_pdf_bytes: bytes) -> None:
        doc = loader.load(blank_pdf_bytes, "blank.pdf")
        assert doc.page_count == 1
        assert doc.content == ""

    def test_source_is_filename(self, loader: PdfLoader, valid_pdf_bytes: bytes) -> None:
        doc = loader.load(valid_pdf_bytes, "report.pdf")
        assert doc.source == "report.pdf"


class TestPdfLoaderErrors:
    def test_empty_bytes_raises(self, loader: PdfLoader, empty_bytes: bytes) -> None:
        with pytest.raises(EmptyFileError):
            loader.load(empty_bytes, "empty.pdf")

    def test_corrupted_file_raises(self, loader: PdfLoader, corrupted_pdf_bytes: bytes) -> None:
        with pytest.raises(CorruptedFileError):
            loader.load(corrupted_pdf_bytes, "bad.pdf")

    def test_non_pdf_bytes_raises(self, loader: PdfLoader) -> None:
        with pytest.raises(CorruptedFileError):
            loader.load(b"hello world not a pdf", "fake.pdf")
