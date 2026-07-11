"""Tests for ValidationService.

Covers all validation branches:
  - valid upload accepted and extension returned
  - dotfile rejected (400)
  - filename too long rejected (400)
  - empty file rejected (400)
  - oversized file rejected (413)
  - unsupported extension rejected (415)
  - duplicate filename rejected (409)
"""
import pytest
from fastapi import HTTPException

from app.services.validation_service import ValidationService


@pytest.fixture
def svc() -> ValidationService:
    return ValidationService()


# ── Valid uploads ──────────────────────────────────────────────────────────────

class TestValidationServiceAccepts:
    def test_valid_pdf_accepted(self, svc: ValidationService) -> None:
        ext = svc.validate("report.pdf", b"x" * 100)
        assert ext == "pdf"

    def test_valid_docx_accepted(self, svc: ValidationService) -> None:
        ext = svc.validate("policy.docx", b"x" * 100)
        assert ext == "docx"

    def test_valid_txt_accepted(self, svc: ValidationService) -> None:
        ext = svc.validate("notes.txt", b"hello world")
        assert ext == "txt"

    def test_valid_csv_accepted(self, svc: ValidationService) -> None:
        ext = svc.validate("data.csv", b"col1,col2\n1,2\n")
        assert ext == "csv"

    def test_valid_xlsx_accepted(self, svc: ValidationService) -> None:
        ext = svc.validate("grades.xlsx", b"x" * 100)
        assert ext == "xlsx"

    def test_returns_lowercase_extension(self, svc: ValidationService) -> None:
        ext = svc.validate("REPORT.PDF", b"x" * 100)
        assert ext == "pdf"

    def test_no_duplicate_check_when_not_provided(self, svc: ValidationService) -> None:
        # existing_filenames=None → no duplicate check, should succeed
        ext = svc.validate("report.pdf", b"x" * 100)
        assert ext == "pdf"

    def test_no_duplicate_if_different_filename(self, svc: ValidationService) -> None:
        existing = frozenset({"other.pdf"})
        ext = svc.validate("report.pdf", b"x" * 100, existing)
        assert ext == "pdf"

    def test_empty_frozenset_does_not_block_upload(self, svc: ValidationService) -> None:
        ext = svc.validate("report.pdf", b"x" * 100, frozenset())
        assert ext == "pdf"


# ── Filename validation ────────────────────────────────────────────────────────

class TestFilenameValidation:
    def test_empty_filename_raises_400(self, svc: ValidationService) -> None:
        with pytest.raises(HTTPException) as exc_info:
            svc.validate("", b"content")
        assert exc_info.value.status_code == 400

    def test_whitespace_only_filename_raises_400(self, svc: ValidationService) -> None:
        with pytest.raises(HTTPException) as exc_info:
            svc.validate("   ", b"content")
        assert exc_info.value.status_code == 400

    def test_dotfile_raises_400(self, svc: ValidationService) -> None:
        with pytest.raises(HTTPException) as exc_info:
            svc.validate(".hidden.pdf", b"content")
        assert exc_info.value.status_code == 400

    def test_dotfile_detail_message(self, svc: ValidationService) -> None:
        with pytest.raises(HTTPException) as exc_info:
            svc.validate(".bashrc", b"content")
        assert "dotfile" in exc_info.value.detail.lower() or "hidden" in exc_info.value.detail.lower()

    def test_filename_exactly_255_chars_accepted(self, svc: ValidationService) -> None:
        # 251 'a' chars + ".pdf" = 255 total
        name = "a" * 251 + ".pdf"
        assert len(name) == 255
        ext = svc.validate(name, b"x" * 100)
        assert ext == "pdf"

    def test_filename_256_chars_raises_400(self, svc: ValidationService) -> None:
        name = "a" * 252 + ".pdf"  # 256 chars
        assert len(name) == 256
        with pytest.raises(HTTPException) as exc_info:
            svc.validate(name, b"content")
        assert exc_info.value.status_code == 400


# ── Extension validation ───────────────────────────────────────────────────────

class TestExtensionValidation:
    def test_pptx_rejected_415(self, svc: ValidationService) -> None:
        with pytest.raises(HTTPException) as exc_info:
            svc.validate("slides.pptx", b"content")
        assert exc_info.value.status_code == 415

    def test_exe_rejected_415(self, svc: ValidationService) -> None:
        with pytest.raises(HTTPException) as exc_info:
            svc.validate("malware.exe", b"content")
        assert exc_info.value.status_code == 415

    def test_no_extension_rejected_415(self, svc: ValidationService) -> None:
        with pytest.raises(HTTPException) as exc_info:
            svc.validate("noextension", b"content")
        assert exc_info.value.status_code == 415

    def test_error_detail_lists_supported_types(self, svc: ValidationService) -> None:
        with pytest.raises(HTTPException) as exc_info:
            svc.validate("report.pptx", b"content")
        detail = exc_info.value.detail
        # Detail should mention at least one supported extension
        assert any(ext in detail for ext in ("pdf", "csv", "docx", "txt", "xlsx"))

    def test_mp4_rejected_415(self, svc: ValidationService) -> None:
        with pytest.raises(HTTPException) as exc_info:
            svc.validate("video.mp4", b"content")
        assert exc_info.value.status_code == 415


# ── Size validation ────────────────────────────────────────────────────────────

class TestSizeValidation:
    def test_empty_file_raises_400(self, svc: ValidationService) -> None:
        with pytest.raises(HTTPException) as exc_info:
            svc.validate("empty.pdf", b"")
        assert exc_info.value.status_code == 400

    def test_empty_file_detail_message(self, svc: ValidationService) -> None:
        with pytest.raises(HTTPException) as exc_info:
            svc.validate("empty.pdf", b"")
        assert "empty" in exc_info.value.detail.lower()

    def test_oversized_file_raises_413(self, svc: ValidationService) -> None:
        oversized = b"x" * (21 * 1024 * 1024)  # 21 MB
        with pytest.raises(HTTPException) as exc_info:
            svc.validate("big.pdf", oversized)
        assert exc_info.value.status_code == 413

    def test_oversized_detail_mentions_limit(self, svc: ValidationService) -> None:
        oversized = b"x" * (21 * 1024 * 1024)
        with pytest.raises(HTTPException) as exc_info:
            svc.validate("big.pdf", oversized)
        assert "20" in exc_info.value.detail  # mentions the 20 MB limit

    def test_exactly_at_limit_accepted(self, svc: ValidationService) -> None:
        at_limit = b"x" * (20 * 1024 * 1024)  # exactly 20 MB
        ext = svc.validate("big.pdf", at_limit)
        assert ext == "pdf"

    def test_one_byte_file_accepted(self, svc: ValidationService) -> None:
        ext = svc.validate("tiny.txt", b"x")
        assert ext == "txt"


# ── Duplicate validation ───────────────────────────────────────────────────────

class TestDuplicateValidation:
    def test_duplicate_filename_raises_409(self, svc: ValidationService) -> None:
        existing = frozenset({"report.pdf"})
        with pytest.raises(HTTPException) as exc_info:
            svc.validate("report.pdf", b"x" * 100, existing)
        assert exc_info.value.status_code == 409

    def test_duplicate_detail_mentions_filename(self, svc: ValidationService) -> None:
        existing = frozenset({"handbook.pdf"})
        with pytest.raises(HTTPException) as exc_info:
            svc.validate("handbook.pdf", b"x" * 100, existing)
        assert "handbook.pdf" in exc_info.value.detail

    def test_same_name_different_case_is_not_duplicate(self, svc: ValidationService) -> None:
        # Filename comparison is case-sensitive (filenames are stored as-uploaded)
        existing = frozenset({"Report.pdf"})
        ext = svc.validate("report.pdf", b"x" * 100, existing)
        assert ext == "pdf"

    def test_multiple_existing_files_no_conflict(self, svc: ValidationService) -> None:
        existing = frozenset({"a.pdf", "b.csv", "c.txt"})
        ext = svc.validate("d.xlsx", b"x" * 100, existing)
        assert ext == "xlsx"

    def test_multiple_existing_files_with_conflict(self, svc: ValidationService) -> None:
        existing = frozenset({"a.pdf", "target.csv", "c.txt"})
        with pytest.raises(HTTPException) as exc_info:
            svc.validate("target.csv", b"x" * 100, existing)
        assert exc_info.value.status_code == 409
