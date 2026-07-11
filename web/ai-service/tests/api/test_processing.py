"""API tests for POST /documents/{id}/process and GET /documents/{id}/chunks."""
import io
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.chunk_service import ChunkService, get_chunk_service
from app.services.document_service import DocumentService, get_document_service
from tests.conftest import GATEWAY_HEADERS
from tests.loaders.conftest import make_text_pdf


# ── Helpers ───────────────────────────────────────────────────────────────────

def _rich_pdf_bytes() -> bytes:
    """PDF with enough text to produce valid chunks at default settings."""
    leave_text = (
        "Leave Policy. "
        "Employees are entitled to twenty days of paid annual leave per calendar year. "
        "Leave requests must be submitted at least two weeks in advance. "
        "Unused leave balances may be carried over to the following year. "
        "Sick leave allowance is ten days per year and requires a medical certificate "
        "when taken for more than three consecutive days. "
    )
    return make_text_pdf(leave_text * 6, pages=3)


def _upload_pdf(client: TestClient) -> dict[str, Any]:
    """Upload a rich PDF and return the JSON body."""
    pdf = _rich_pdf_bytes()
    res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("handbook.pdf", io.BytesIO(pdf), "application/pdf")},
        headers=GATEWAY_HEADERS,
    )
    assert res.status_code == 201, res.text
    return res.json()


def _process(
    client: TestClient,
    document_id: str,
    chunk_size: int = 200,
    overlap: int = 30,
    min_tokens: int = 5,
) -> Any:
    return client.post(
        f"/api/v1/documents/{document_id}/process"
        f"?chunk_size={chunk_size}&overlap={overlap}&min_tokens={min_tokens}",
        headers=GATEWAY_HEADERS,
    )


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def proc_client() -> Generator[TestClient, None, None]:
    """TestClient with isolated DocumentService + ChunkService per test."""
    doc_service = DocumentService()
    chunk_service = ChunkService()
    app = create_app()
    app.dependency_overrides[get_document_service] = lambda: doc_service
    app.dependency_overrides[get_chunk_service] = lambda: chunk_service
    with TestClient(app) as client:
        yield client


# ── POST /documents/{id}/process ──────────────────────────────────────────────

class TestProcessEndpoint:
    def test_process_returns_200(self, proc_client: TestClient) -> None:
        doc = _upload_pdf(proc_client)
        res = _process(proc_client, doc["document_id"])
        assert res.status_code == 200

    def test_process_response_shape(self, proc_client: TestClient) -> None:
        doc = _upload_pdf(proc_client)
        res = _process(proc_client, doc["document_id"])
        body = res.json()
        assert body["success"] is True
        assert body["document_id"] == doc["document_id"]
        assert body["filename"] == "handbook.pdf"
        assert "chunks_created" in body
        assert "total_tokens" in body
        assert "average_tokens" in body
        assert "largest_chunk" in body
        assert "smallest_chunk" in body

    def test_process_creates_chunks(self, proc_client: TestClient) -> None:
        doc = _upload_pdf(proc_client)
        body = _process(proc_client, doc["document_id"]).json()
        assert body["chunks_created"] > 0

    def test_process_unknown_document_returns_404(self, proc_client: TestClient) -> None:
        res = _process(proc_client, "00000000-0000-0000-0000-000000000000")
        assert res.status_code == 404

    def test_process_requires_internal_token(self, proc_client: TestClient) -> None:
        doc = _upload_pdf(proc_client)
        res = proc_client.post(
            f"/api/v1/documents/{doc['document_id']}/process"
            "?chunk_size=200&overlap=30&min_tokens=5"
        )
        assert res.status_code == 401

    def test_process_invalid_chunk_size_returns_422(self, proc_client: TestClient) -> None:
        doc = _upload_pdf(proc_client)
        res = proc_client.post(
            f"/api/v1/documents/{doc['document_id']}/process"
            "?chunk_size=50&overlap=10&min_tokens=5",
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 422

    def test_process_overlap_ge_chunk_size_returns_422(self, proc_client: TestClient) -> None:
        doc = _upload_pdf(proc_client)
        res = proc_client.post(
            f"/api/v1/documents/{doc['document_id']}/process"
            "?chunk_size=200&overlap=200&min_tokens=5",
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 422

    def test_process_twice_overwrites_chunks(self, proc_client: TestClient) -> None:
        doc = _upload_pdf(proc_client)
        first = _process(proc_client, doc["document_id"]).json()
        second = _process(proc_client, doc["document_id"]).json()
        # Both calls succeed and agree on chunk count
        assert first["chunks_created"] == second["chunks_created"]


# ── GET /documents/{id}/chunks ────────────────────────────────────────────────

class TestListChunksEndpoint:
    def test_list_chunks_returns_200_after_processing(
        self, proc_client: TestClient
    ) -> None:
        doc = _upload_pdf(proc_client)
        _process(proc_client, doc["document_id"])
        res = proc_client.get(
            f"/api/v1/documents/{doc['document_id']}/chunks",
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 200

    def test_list_chunks_returns_empty_list_before_processing(
        self, proc_client: TestClient
    ) -> None:
        doc = _upload_pdf(proc_client)
        res = proc_client.get(
            f"/api/v1/documents/{doc['document_id']}/chunks",
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 200
        assert res.json() == []

    def test_list_chunks_count_matches_summary(self, proc_client: TestClient) -> None:
        doc = _upload_pdf(proc_client)
        summary = _process(proc_client, doc["document_id"]).json()
        res = proc_client.get(
            f"/api/v1/documents/{doc['document_id']}/chunks",
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 200
        assert len(res.json()) == summary["chunks_created"]

    def test_list_chunks_response_item_shape(self, proc_client: TestClient) -> None:
        doc = _upload_pdf(proc_client)
        _process(proc_client, doc["document_id"])
        items = proc_client.get(
            f"/api/v1/documents/{doc['document_id']}/chunks",
            headers=GATEWAY_HEADERS,
        ).json()
        if not items:
            pytest.skip("No chunks produced — skip schema check")
        item = items[0]
        assert "chunk_id" in item
        assert "chunk_index" in item
        assert "token_count" in item
        assert "text_preview" in item

    def test_list_chunks_unknown_document_returns_404(
        self, proc_client: TestClient
    ) -> None:
        res = proc_client.get(
            "/api/v1/documents/00000000-0000-0000-0000-000000000000/chunks",
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 404

    def test_list_chunks_requires_internal_token(self, proc_client: TestClient) -> None:
        doc = _upload_pdf(proc_client)
        _process(proc_client, doc["document_id"])
        res = proc_client.get(
            f"/api/v1/documents/{doc['document_id']}/chunks",
        )
        assert res.status_code == 401

    def test_text_preview_max_200_chars(self, proc_client: TestClient) -> None:
        doc = _upload_pdf(proc_client)
        _process(proc_client, doc["document_id"])
        items = proc_client.get(
            f"/api/v1/documents/{doc['document_id']}/chunks",
            headers=GATEWAY_HEADERS,
        ).json()
        for item in items:
            assert len(item["text_preview"]) <= 200

    def test_chunk_indexes_are_sequential(self, proc_client: TestClient) -> None:
        doc = _upload_pdf(proc_client)
        _process(proc_client, doc["document_id"])
        items = proc_client.get(
            f"/api/v1/documents/{doc['document_id']}/chunks",
            headers=GATEWAY_HEADERS,
        ).json()
        indexes = [item["chunk_index"] for item in items]
        assert indexes == list(range(len(items)))
