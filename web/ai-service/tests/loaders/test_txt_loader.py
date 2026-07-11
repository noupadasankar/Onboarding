"""Tests for TxtLoader."""
import pytest

from app.loaders.exceptions import EmptyFileError, InvalidEncodingError
from app.loaders.txt_loader import TxtLoader
from app.models.document import FileType


@pytest.fixture
def loader() -> TxtLoader:
    return TxtLoader()


class TestTxtLoaderValid:
    def test_file_type(self, loader: TxtLoader) -> None:
        assert loader.file_type == "txt"

    def test_returns_document_model(self, loader: TxtLoader, valid_txt_bytes: bytes) -> None:
        doc = loader.load(valid_txt_bytes, "onboarding.txt")
        assert doc.filename == "onboarding.txt"
        assert doc.file_type == FileType.TXT
        assert doc.mime_type == "text/plain"

    def test_text_extracted(self, loader: TxtLoader, valid_txt_bytes: bytes) -> None:
        doc = loader.load(valid_txt_bytes, "onboarding.txt")
        assert "Onboarding Process" in doc.content
        assert "Day 1" in doc.content

    def test_metadata_encoding_utf8(self, loader: TxtLoader, valid_txt_bytes: bytes) -> None:
        doc = loader.load(valid_txt_bytes, "onboarding.txt")
        assert doc.metadata["encoding"] == "utf-8"

    def test_metadata_line_count(self, loader: TxtLoader, valid_txt_bytes: bytes) -> None:
        doc = loader.load(valid_txt_bytes, "onboarding.txt")
        assert doc.metadata["line_count"] == 5

    def test_metadata_word_count(self, loader: TxtLoader, valid_txt_bytes: bytes) -> None:
        doc = loader.load(valid_txt_bytes, "onboarding.txt")
        assert doc.metadata.get("word_count", 0) > 0

    def test_latin1_decoded(self, loader: TxtLoader, latin1_txt_bytes: bytes) -> None:
        doc = loader.load(latin1_txt_bytes, "legacy.txt")
        assert "Caf" in doc.content
        assert doc.metadata["encoding"] != "utf-8"

    def test_page_count_is_none(self, loader: TxtLoader, valid_txt_bytes: bytes) -> None:
        doc = loader.load(valid_txt_bytes, "onboarding.txt")
        assert doc.page_count is None

    def test_size_bytes_correct(self, loader: TxtLoader, valid_txt_bytes: bytes) -> None:
        doc = loader.load(valid_txt_bytes, "onboarding.txt")
        assert doc.size_bytes == len(valid_txt_bytes)


class TestTxtLoaderErrors:
    def test_empty_bytes_raises(self, loader: TxtLoader, empty_bytes: bytes) -> None:
        with pytest.raises(EmptyFileError):
            loader.load(empty_bytes, "empty.txt")

    def test_binary_garbage_raises(self, loader: TxtLoader) -> None:
        garbage = bytes(range(256)) * 4
        with pytest.raises((InvalidEncodingError, EmptyFileError)):
            loader.load(garbage, "garbage.txt")
