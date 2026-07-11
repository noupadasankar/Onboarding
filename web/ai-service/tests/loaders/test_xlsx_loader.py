"""Tests for XlsxLoader."""
import pytest

from app.loaders.exceptions import CorruptedFileError, EmptyFileError
from app.loaders.xlsx_loader import XlsxLoader
from app.models.document import FileType


@pytest.fixture
def loader() -> XlsxLoader:
    return XlsxLoader()


class TestXlsxLoaderValid:
    def test_file_type(self, loader: XlsxLoader) -> None:
        assert loader.file_type == "xlsx"

    def test_returns_document_model(self, loader: XlsxLoader, valid_xlsx_bytes: bytes) -> None:
        doc = loader.load(valid_xlsx_bytes, "Salary_Grades.xlsx")
        assert doc.filename == "Salary_Grades.xlsx"
        assert doc.file_type == FileType.XLSX
        assert "spreadsheetml" in doc.mime_type

    def test_content_contains_sheet_header(
        self, loader: XlsxLoader, valid_xlsx_bytes: bytes
    ) -> None:
        doc = loader.load(valid_xlsx_bytes, "Salary_Grades.xlsx")
        assert "[Sheet: Salary Grades]" in doc.content
        assert "[Sheet: Holiday Calendar]" in doc.content

    def test_content_contains_data(self, loader: XlsxLoader, valid_xlsx_bytes: bytes) -> None:
        doc = loader.load(valid_xlsx_bytes, "Salary_Grades.xlsx")
        assert "30000" in doc.content or "A" in doc.content

    def test_metadata_sheet_names(self, loader: XlsxLoader, valid_xlsx_bytes: bytes) -> None:
        doc = loader.load(valid_xlsx_bytes, "Salary_Grades.xlsx")
        assert "Salary Grades" in doc.metadata["sheet_names"]
        assert "Holiday Calendar" in doc.metadata["sheet_names"]

    def test_metadata_sheet_count(self, loader: XlsxLoader, valid_xlsx_bytes: bytes) -> None:
        doc = loader.load(valid_xlsx_bytes, "Salary_Grades.xlsx")
        assert doc.metadata["sheet_count"] == 2

    def test_metadata_row_counts(self, loader: XlsxLoader, valid_xlsx_bytes: bytes) -> None:
        doc = loader.load(valid_xlsx_bytes, "Salary_Grades.xlsx")
        sheets = doc.metadata["sheets"]
        assert sheets["Salary Grades"]["row_count"] == 3
        assert sheets["Holiday Calendar"]["row_count"] == 2

    def test_metadata_column_names(self, loader: XlsxLoader, valid_xlsx_bytes: bytes) -> None:
        doc = loader.load(valid_xlsx_bytes, "Salary_Grades.xlsx")
        cols = doc.metadata["sheets"]["Salary Grades"]["column_names"]
        assert cols == ["Grade", "Min Salary", "Max Salary"]

    def test_page_count_is_none(self, loader: XlsxLoader, valid_xlsx_bytes: bytes) -> None:
        doc = loader.load(valid_xlsx_bytes, "Salary_Grades.xlsx")
        assert doc.page_count is None

    def test_size_bytes_correct(self, loader: XlsxLoader, valid_xlsx_bytes: bytes) -> None:
        doc = loader.load(valid_xlsx_bytes, "Salary_Grades.xlsx")
        assert doc.size_bytes == len(valid_xlsx_bytes)


class TestXlsxLoaderErrors:
    def test_empty_bytes_raises(self, loader: XlsxLoader, empty_bytes: bytes) -> None:
        with pytest.raises(EmptyFileError):
            loader.load(empty_bytes, "empty.xlsx")

    def test_corrupted_file_raises(self, loader: XlsxLoader, corrupted_xlsx_bytes: bytes) -> None:
        with pytest.raises(CorruptedFileError):
            loader.load(corrupted_xlsx_bytes, "bad.xlsx")

    def test_txt_bytes_as_xlsx_raises(self, loader: XlsxLoader, valid_txt_bytes: bytes) -> None:
        with pytest.raises(CorruptedFileError):
            loader.load(valid_txt_bytes, "fake.xlsx")
