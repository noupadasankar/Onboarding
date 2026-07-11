"""Tests for DocxLoader."""
import pytest

from app.loaders.docx_loader import DocxLoader
from app.loaders.exceptions import CorruptedFileError, EmptyFileError
from app.models.document import FileType


@pytest.fixture
def loader() -> DocxLoader:
    return DocxLoader()


class TestDocxLoaderValid:
    def test_file_type(self, loader: DocxLoader) -> None:
        assert loader.file_type == "docx"

    def test_returns_document_model(self, loader: DocxLoader, valid_docx_bytes: bytes) -> None:
        doc = loader.load(valid_docx_bytes, "policy.docx")
        assert doc.filename == "policy.docx"
        assert doc.file_type == FileType.DOCX
        assert "wordprocessingml" in doc.mime_type

    def test_text_extracted(self, loader: DocxLoader, valid_docx_bytes: bytes) -> None:
        doc = loader.load(valid_docx_bytes, "policy.docx")
        assert "Company Policy" in doc.content or "code of conduct" in doc.content

    def test_metadata_author(self, loader: DocxLoader, valid_docx_bytes: bytes) -> None:
        doc = loader.load(valid_docx_bytes, "policy.docx")
        assert doc.metadata.get("author") == "HR Department"

    def test_metadata_title(self, loader: DocxLoader, valid_docx_bytes: bytes) -> None:
        doc = loader.load(valid_docx_bytes, "policy.docx")
        assert doc.metadata.get("title") == "Company Policy"

    def test_metadata_word_count(self, loader: DocxLoader, valid_docx_bytes: bytes) -> None:
        doc = loader.load(valid_docx_bytes, "policy.docx")
        assert doc.metadata.get("word_count", 0) > 0

    def test_page_count_is_none(self, loader: DocxLoader, valid_docx_bytes: bytes) -> None:
        doc = loader.load(valid_docx_bytes, "policy.docx")
        assert doc.page_count is None

    def test_size_bytes_correct(self, loader: DocxLoader, valid_docx_bytes: bytes) -> None:
        doc = loader.load(valid_docx_bytes, "policy.docx")
        assert doc.size_bytes == len(valid_docx_bytes)


class TestDocxLoaderErrors:
    def test_empty_bytes_raises(self, loader: DocxLoader, empty_bytes: bytes) -> None:
        with pytest.raises(EmptyFileError):
            loader.load(empty_bytes, "empty.docx")

    def test_corrupted_file_raises(self, loader: DocxLoader, corrupted_docx_bytes: bytes) -> None:
        with pytest.raises(CorruptedFileError):
            loader.load(corrupted_docx_bytes, "bad.docx")

    def test_txt_bytes_as_docx_raises(self, loader: DocxLoader, valid_txt_bytes: bytes) -> None:
        with pytest.raises(CorruptedFileError):
            loader.load(valid_txt_bytes, "fake.docx")
