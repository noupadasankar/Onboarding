"""Tests for CsvLoader."""
import pytest

from app.loaders.csv_loader import CsvLoader
from app.loaders.exceptions import EmptyFileError
from app.models.document import FileType


@pytest.fixture
def loader() -> CsvLoader:
    return CsvLoader()


class TestCsvLoaderValid:
    def test_file_type(self, loader: CsvLoader) -> None:
        assert loader.file_type == "csv"

    def test_returns_document_model(self, loader: CsvLoader, valid_csv_bytes: bytes) -> None:
        doc = loader.load(valid_csv_bytes, "HR_FAQs.csv")
        assert doc.filename == "HR_FAQs.csv"
        assert doc.file_type == FileType.CSV
        assert doc.mime_type == "text/csv"

    def test_content_contains_data(self, loader: CsvLoader, valid_csv_bytes: bytes) -> None:
        doc = loader.load(valid_csv_bytes, "HR_FAQs.csv")
        assert "Alice" in doc.content
        assert "HR" in doc.content

    def test_metadata_column_names(self, loader: CsvLoader, valid_csv_bytes: bytes) -> None:
        doc = loader.load(valid_csv_bytes, "HR_FAQs.csv")
        assert doc.metadata["column_names"] == ["name", "department", "leave_days"]

    def test_metadata_row_count(self, loader: CsvLoader, valid_csv_bytes: bytes) -> None:
        doc = loader.load(valid_csv_bytes, "HR_FAQs.csv")
        assert doc.metadata["row_count"] == 3

    def test_metadata_column_count(self, loader: CsvLoader, valid_csv_bytes: bytes) -> None:
        doc = loader.load(valid_csv_bytes, "HR_FAQs.csv")
        assert doc.metadata["column_count"] == 3

    def test_bom_stripped(self, loader: CsvLoader, csv_with_bom_bytes: bytes) -> None:
        doc = loader.load(csv_with_bom_bytes, "bom.csv")
        assert doc.metadata["column_names"][0] == "name"

    def test_page_count_is_none(self, loader: CsvLoader, valid_csv_bytes: bytes) -> None:
        doc = loader.load(valid_csv_bytes, "HR_FAQs.csv")
        assert doc.page_count is None

    def test_size_bytes_correct(self, loader: CsvLoader, valid_csv_bytes: bytes) -> None:
        doc = loader.load(valid_csv_bytes, "HR_FAQs.csv")
        assert doc.size_bytes == len(valid_csv_bytes)


class TestCsvLoaderErrors:
    def test_empty_bytes_raises(self, loader: CsvLoader, empty_bytes: bytes) -> None:
        with pytest.raises(EmptyFileError):
            loader.load(empty_bytes, "empty.csv")
