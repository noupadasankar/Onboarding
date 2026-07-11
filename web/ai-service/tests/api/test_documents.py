"""End-to-end API tests for the document endpoints.

Each test class uses a fresh DocumentService injected via FastAPI's
dependency_overrides, so document state does not leak between tests.
"""
import io
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.document_service import DocumentService, get_document_service
from tests.conftest import GATEWAY_HEADERS
from tests.loaders.conftest import make_docx, make_text_pdf, make_xlsx


def _upload(client: TestClient, content: bytes, filename: str) -> Any:
    return client.post(
        "/api/v1/documents/upload",
        files={"file": (filename, io.BytesIO(content), "application/octet-stream")},
        headers=GATEWAY_HEADERS,
    )


@pytest.fixture
def doc_client() -> Generator[TestClient, None, None]:
    """TestClient with a fresh in-memory DocumentService per test."""
    service = DocumentService()
    app = create_app()
    app.dependency_overrides[get_document_service] = lambda: service
    with TestClient(app) as client:
        yield client


class TestUploadEndpoint:
    def test_upload_pdf_returns_201(self, doc_client: TestClient) -> None:
        pdf = make_text_pdf("Employee Handbook", pages=1)
        res = _upload(doc_client, pdf, "handbook.pdf")
        assert res.status_code == 201

    def test_upload_response_shape(self, doc_client: TestClient) -> None:
        pdf = make_text_pdf("Leave Policy", pages=1)
        res = _upload(doc_client, pdf, "leave.pdf")
        data = res.json()
        assert "document_id" in data
        assert data["filename"] == "leave.pdf"
        assert data["file_type"] == "pdf"
        assert "content" in data
        assert "content_length" in data
        assert "metadata" in data
        assert data["page_count"] == 1

    def test_upload_docx_returns_201(self, doc_client: TestClient) -> None:
        docx = make_docx(["Company Policy"], title="Policy", author="HR")
        res = _upload(doc_client, docx, "policy.docx")
        assert res.status_code == 201
        assert res.json()["file_type"] == "docx"

    def test_upload_csv_returns_201(self, doc_client: TestClient) -> None:
        csv_bytes = b"name,dept\nAlice,HR\nBob,IT\n"
        res = _upload(doc_client, csv_bytes, "employees.csv")
        assert res.status_code == 201
        assert res.json()["file_type"] == "csv"

    def test_upload_txt_returns_201(self, doc_client: TestClient) -> None:
        txt = b"Onboarding: Day 1 - Meet your manager."
        res = _upload(doc_client, txt, "onboarding.txt")
        assert res.status_code == 201
        assert res.json()["file_type"] == "txt"

    def test_upload_xlsx_returns_201(self, doc_client: TestClient) -> None:
        xlsx = make_xlsx({"Grades": [["Grade", "Min"], ["A", "30000"]]})
        res = _upload(doc_client, xlsx, "grades.xlsx")
        assert res.status_code == 201
        assert res.json()["file_type"] == "xlsx"

    def test_upload_requires_internal_token(self, doc_client: TestClient) -> None:
        pdf = make_text_pdf("test", pages=1)
        res = doc_client.post(
            "/api/v1/documents/upload",
            files={"file": ("doc.pdf", io.BytesIO(pdf), "application/pdf")},
        )
        assert res.status_code == 401

    def test_upload_unsupported_type_returns_415(self, doc_client: TestClient) -> None:
        res = _upload(doc_client, b"data", "report.pptx")
        assert res.status_code == 415

    def test_upload_empty_file_returns_400(self, doc_client: TestClient) -> None:
        res = _upload(doc_client, b"", "empty.pdf")
        assert res.status_code == 400

    def test_upload_corrupted_pdf_returns_422(self, doc_client: TestClient) -> None:
        res = _upload(doc_client, b"%PDF-1.4 garbage", "bad.pdf")
        assert res.status_code == 422

    def test_upload_uploaded_by_is_user_id(self, doc_client: TestClient) -> None:
        pdf = make_text_pdf("Test", pages=1)
        res = _upload(doc_client, pdf, "test.pdf")
        assert res.json()["uploaded_by"] == "u_test"


class TestListEndpoint:
    def test_empty_list(self, doc_client: TestClient) -> None:
        res = doc_client.get("/api/v1/documents", headers=GATEWAY_HEADERS)
        assert res.status_code == 200
        assert res.json() == []

    def test_lists_uploaded_documents(self, doc_client: TestClient) -> None:
        _upload(doc_client, make_text_pdf("A", pages=1), "a.pdf")
        _upload(doc_client, b"col1,col2\n1,2\n", "b.csv")
        res = doc_client.get("/api/v1/documents", headers=GATEWAY_HEADERS)
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_list_response_excludes_content(self, doc_client: TestClient) -> None:
        _upload(doc_client, make_text_pdf("Test", pages=1), "test.pdf")
        res = doc_client.get("/api/v1/documents", headers=GATEWAY_HEADERS)
        item = res.json()[0]
        assert "content" not in item

    def test_list_requires_internal_token(self, doc_client: TestClient) -> None:
        res = doc_client.get("/api/v1/documents")
        assert res.status_code == 401


class TestGetEndpoint:
    def test_get_by_id_includes_content(self, doc_client: TestClient) -> None:
        pdf = make_text_pdf("HR Handbook", pages=1)
        upload_res = _upload(doc_client, pdf, "handbook.pdf")
        doc_id = upload_res.json()["document_id"]

        res = doc_client.get(f"/api/v1/documents/{doc_id}", headers=GATEWAY_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "content" in data
        assert data["document_id"] == doc_id

    def test_get_missing_returns_404(self, doc_client: TestClient) -> None:
        res = doc_client.get("/api/v1/documents/no-such-id", headers=GATEWAY_HEADERS)
        assert res.status_code == 404

    def test_get_requires_internal_token(self, doc_client: TestClient) -> None:
        res = doc_client.get("/api/v1/documents/any-id")
        assert res.status_code == 401


class TestDeleteEndpoint:
    def test_delete_returns_204(self, doc_client: TestClient) -> None:
        pdf = make_text_pdf("Policy", pages=1)
        upload_res = _upload(doc_client, pdf, "policy.pdf")
        doc_id = upload_res.json()["document_id"]

        res = doc_client.delete(f"/api/v1/documents/{doc_id}", headers=GATEWAY_HEADERS)
        assert res.status_code == 204

    def test_delete_removes_from_list(self, doc_client: TestClient) -> None:
        pdf = make_text_pdf("Policy", pages=1)
        upload_res = _upload(doc_client, pdf, "policy.pdf")
        doc_id = upload_res.json()["document_id"]

        doc_client.delete(f"/api/v1/documents/{doc_id}", headers=GATEWAY_HEADERS)
        res = doc_client.get("/api/v1/documents", headers=GATEWAY_HEADERS)
        assert res.json() == []

    def test_delete_missing_returns_404(self, doc_client: TestClient) -> None:
        res = doc_client.delete("/api/v1/documents/no-such-id", headers=GATEWAY_HEADERS)
        assert res.status_code == 404

    def test_delete_requires_internal_token(self, doc_client: TestClient) -> None:
        res = doc_client.delete("/api/v1/documents/any-id")
        assert res.status_code == 401


class TestDuplicateUpload:
    def test_duplicate_filename_returns_409(self, doc_client: TestClient) -> None:
        pdf = make_text_pdf("Policy text", pages=1)
        _upload(doc_client, pdf, "policy.pdf")
        res = _upload(doc_client, pdf, "policy.pdf")
        assert res.status_code == 409

    def test_duplicate_detail_mentions_filename(self, doc_client: TestClient) -> None:
        pdf = make_text_pdf("Handbook", pages=1)
        _upload(doc_client, pdf, "handbook.pdf")
        res = _upload(doc_client, pdf, "handbook.pdf")
        assert "handbook.pdf" in res.json().get("detail", "")

    def test_different_filename_not_blocked(self, doc_client: TestClient) -> None:
        pdf = make_text_pdf("Policy text", pages=1)
        res1 = _upload(doc_client, pdf, "policy_v1.pdf")
        res2 = _upload(doc_client, pdf, "policy_v2.pdf")
        assert res1.status_code == 201
        assert res2.status_code == 201

    def test_deleted_filename_can_be_reuploaded(self, doc_client: TestClient) -> None:
        pdf = make_text_pdf("Original", pages=1)
        upload_res = _upload(doc_client, pdf, "reuse.pdf")
        doc_id = upload_res.json()["document_id"]
        doc_client.delete(f"/api/v1/documents/{doc_id}", headers=GATEWAY_HEADERS)
        # After deletion the same filename should be accepted again
        res = _upload(doc_client, pdf, "reuse.pdf")
        assert res.status_code == 201


class TestWordCountInResponse:
    def test_word_count_present_in_upload_response(self, doc_client: TestClient) -> None:
        txt = b"The quick brown fox jumped over the lazy dog"
        res = _upload(doc_client, txt, "sentence.txt")
        assert res.status_code == 201
        assert "word_count" in res.json()

    def test_word_count_is_non_negative(self, doc_client: TestClient) -> None:
        txt = b"One two three four five six seven eight nine ten"
        res = _upload(doc_client, txt, "words.txt")
        assert res.json()["word_count"] >= 0

    def test_word_count_positive_for_real_content(self, doc_client: TestClient) -> None:
        txt = b"HR document containing meaningful words for counting purposes"
        res = _upload(doc_client, txt, "hr_doc.txt")
        assert res.json()["word_count"] > 0

    def test_word_count_in_list_response(self, doc_client: TestClient) -> None:
        txt = b"HR document with some words in it"
        _upload(doc_client, txt, "hr_list.txt")
        res = doc_client.get("/api/v1/documents", headers=GATEWAY_HEADERS)
        assert res.status_code == 200
        assert "word_count" in res.json()[0]

    def test_word_count_in_get_by_id_response(self, doc_client: TestClient) -> None:
        txt = b"Some content for word counting"
        upload_res = _upload(doc_client, txt, "word_test.txt")
        doc_id = upload_res.json()["document_id"]
        res = doc_client.get(f"/api/v1/documents/{doc_id}", headers=GATEWAY_HEADERS)
        assert "word_count" in res.json()
