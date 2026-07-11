"""Tests for MetadataService.

Verifies that enrich() correctly adds system-level metadata and
HR context to a Document produced by a loader.
"""
import pytest

from app.models.document import Document, FileType
from app.services.metadata_service import MetadataService


def _make_doc(
    content: str = "Hello world",
    filename: str = "test.pdf",
    file_type: FileType = FileType.PDF,
) -> Document:
    """Return a minimal Document for testing; all required fields set."""
    return Document(
        filename=filename,
        file_type=file_type,
        mime_type="application/pdf",
        content=content,
        metadata={},
        source=filename,
        size_bytes=len(content.encode()),
    )


@pytest.fixture
def svc() -> MetadataService:
    return MetadataService()


@pytest.fixture
def raw_content() -> bytes:
    return b"x" * 2048


# ── Core enrichment fields ─────────────────────────────────────────────────────

class TestCoreEnrichment:
    def test_word_count_added(self, svc: MetadataService, raw_content: bytes) -> None:
        doc = _make_doc("Hello world from HR")
        svc.enrich(doc, raw_content)
        assert doc.metadata["word_count"] == 4

    def test_word_count_single_word(self, svc: MetadataService, raw_content: bytes) -> None:
        doc = _make_doc("Hello")
        svc.enrich(doc, raw_content)
        assert doc.metadata["word_count"] == 1

    def test_char_count_added(self, svc: MetadataService, raw_content: bytes) -> None:
        doc = _make_doc("Hello world")
        svc.enrich(doc, raw_content)
        assert doc.metadata["char_count"] == 11

    def test_file_size_bytes_reflects_raw_content(self, svc: MetadataService) -> None:
        content_bytes = b"x" * 5000
        doc = _make_doc("some text")
        svc.enrich(doc, content_bytes)
        assert doc.metadata["file_size_bytes"] == 5000

    def test_extension_added_for_pdf(self, svc: MetadataService, raw_content: bytes) -> None:
        doc = _make_doc(filename="handbook.pdf")
        svc.enrich(doc, raw_content)
        assert doc.metadata["extension"] == "pdf"

    def test_extension_added_for_csv(self, svc: MetadataService, raw_content: bytes) -> None:
        doc = _make_doc(filename="data.csv", file_type=FileType.CSV)
        svc.enrich(doc, raw_content)
        assert doc.metadata["extension"] == "csv"

    def test_mime_type_added_for_csv(self, svc: MetadataService, raw_content: bytes) -> None:
        doc = _make_doc(filename="data.csv", file_type=FileType.CSV)
        svc.enrich(doc, raw_content)
        assert doc.metadata["mime_type"] == "text/csv"

    def test_enriched_at_is_iso_timestamp(self, svc: MetadataService, raw_content: bytes) -> None:
        doc = _make_doc()
        svc.enrich(doc, raw_content)
        ts = doc.metadata.get("enriched_at", "")
        assert isinstance(ts, str)
        assert "T" in ts  # ISO 8601 uses 'T' separator between date and time

    def test_returns_same_document_instance(self, svc: MetadataService, raw_content: bytes) -> None:
        doc = _make_doc()
        returned = svc.enrich(doc, raw_content)
        assert returned is doc

    def test_empty_content_word_count_is_zero(
        self, svc: MetadataService, raw_content: bytes
    ) -> None:
        doc = _make_doc(content="")
        svc.enrich(doc, raw_content)
        assert doc.metadata["word_count"] == 0

    def test_whitespace_only_content_word_count_is_zero(
        self, svc: MetadataService, raw_content: bytes
    ) -> None:
        doc = _make_doc(content="   \n\n\t  ")
        svc.enrich(doc, raw_content)
        assert doc.metadata["word_count"] == 0


# ── Department enrichment ──────────────────────────────────────────────────────

class TestDepartmentEnrichment:
    def test_department_added_when_provided(
        self, svc: MetadataService, raw_content: bytes
    ) -> None:
        doc = _make_doc()
        svc.enrich(doc, raw_content, department="HR")
        assert doc.metadata["department"] == "HR"

    def test_department_not_in_metadata_when_none(
        self, svc: MetadataService, raw_content: bytes
    ) -> None:
        doc = _make_doc()
        svc.enrich(doc, raw_content, department=None)
        assert "department" not in doc.metadata

    def test_department_not_in_metadata_when_omitted(
        self, svc: MetadataService, raw_content: bytes
    ) -> None:
        doc = _make_doc()
        svc.enrich(doc, raw_content)
        assert "department" not in doc.metadata

    def test_department_engineering(self, svc: MetadataService, raw_content: bytes) -> None:
        doc = _make_doc()
        svc.enrich(doc, raw_content, department="Engineering")
        assert doc.metadata["department"] == "Engineering"


# ── Category inference ─────────────────────────────────────────────────────────

class TestCategoryInference:
    @pytest.mark.parametrize("filename,expected", [
        ("Employee_Handbook.pdf", "policy"),
        ("Company_Policy.docx", "policy"),
        ("Code_of_Conduct.pdf", "policy"),
        ("Leave_Policy.pdf", "leave"),
        ("Holiday_Calendar.csv", "leave"),
        ("Vacation_Schedule.xlsx", "leave"),
        ("Salary_Grades.xlsx", "compensation"),
        ("Pay_Scale.pdf", "compensation"),
        ("Compensation_Guide.pdf", "compensation"),
        ("HR_FAQs.csv", "faq"),
        ("Frequently_Asked_Questions.pdf", "faq"),
        ("Onboarding_Process.txt", "onboarding"),
        ("Orientation_Guide.pdf", "onboarding"),
        ("Random_Document.pdf", "general"),
        ("Meeting_Notes.txt", "general"),
    ])
    def test_category_inferred(
        self,
        svc: MetadataService,
        raw_content: bytes,
        filename: str,
        expected: str,
    ) -> None:
        doc = _make_doc(filename=filename)
        svc.enrich(doc, raw_content)
        assert doc.metadata["category"] == expected

    def test_category_always_present(self, svc: MetadataService, raw_content: bytes) -> None:
        doc = _make_doc(filename="unknown_file.pdf")
        svc.enrich(doc, raw_content)
        assert "category" in doc.metadata

    def test_category_is_string(self, svc: MetadataService, raw_content: bytes) -> None:
        doc = _make_doc(filename="Employee_Handbook.pdf")
        svc.enrich(doc, raw_content)
        assert isinstance(doc.metadata["category"], str)


# ── Loader metadata is preserved ──────────────────────────────────────────────

class TestLoaderMetadataPreserved:
    def test_existing_page_count_not_overwritten(
        self, svc: MetadataService, raw_content: bytes
    ) -> None:
        doc = _make_doc()
        doc.metadata = {"page_count": 42, "author": "HR Team"}
        svc.enrich(doc, raw_content)
        assert doc.metadata["page_count"] == 42
        assert doc.metadata["author"] == "HR Team"

    def test_new_fields_merged_alongside_loader_fields(
        self, svc: MetadataService, raw_content: bytes
    ) -> None:
        doc = _make_doc(content="one two three")
        doc.metadata = {"title": "HR Handbook"}
        svc.enrich(doc, raw_content)
        assert doc.metadata["title"] == "HR Handbook"
        assert doc.metadata["word_count"] == 3

    def test_sheet_count_from_xlsx_preserved(
        self, svc: MetadataService, raw_content: bytes
    ) -> None:
        doc = _make_doc(filename="grades.xlsx", file_type=FileType.XLSX)
        doc.metadata = {"sheet_count": 3, "sheet_names": ["Sheet1", "Sheet2", "Sheet3"]}
        svc.enrich(doc, raw_content)
        assert doc.metadata["sheet_count"] == 3
        assert doc.metadata["sheet_names"] == ["Sheet1", "Sheet2", "Sheet3"]
