"""API integration tests for vectorstore endpoints (in-memory Chroma)."""
import io
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.chunk_service import ChunkService, get_chunk_service
from app.services.document_service import DocumentService, get_document_service
from app.services.vector_service import VectorService, get_vector_service
from app.vectorstore.chroma_client import ChromaClient
from app.repositories.vector_repository import VectorRepository
from tests.conftest import GATEWAY_HEADERS
from tests.loaders.conftest import make_text_pdf


def _make_pdf() -> bytes:
    text = (
        "Employee Leave Policy. "
        "Employees are entitled to twenty days of paid annual leave per year. "
        "Requests must be submitted at least two weeks in advance. "
        "Unused leave may be carried over subject to line manager approval. "
    ) * 8
    return make_text_pdf(text, pages=2)


@pytest.fixture
def vs_client() -> Generator[TestClient, None, None]:
    """TestClient with isolated in-memory services."""
    doc_svc = DocumentService()
    chunk_svc = ChunkService()

    # In-memory Chroma
    mem_client = ChromaClient(mode="memory")
    repo = VectorRepository(client=mem_client, collection_name="test_col")
    vec_svc = VectorService(repo)

    app = create_app()
    app.dependency_overrides[get_document_service] = lambda: doc_svc
    app.dependency_overrides[get_chunk_service] = lambda: chunk_svc
    app.dependency_overrides[get_vector_service] = lambda: vec_svc

    with TestClient(app) as client:
        yield client


def _upload_pdf(client: TestClient) -> dict[str, Any]:
    pdf = _make_pdf()
    res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("handbook.pdf", io.BytesIO(pdf), "application/pdf")},
        headers=GATEWAY_HEADERS,
    )
    assert res.status_code == 201, res.text
    return res.json()


class TestIndexEndpoint:
    def test_index_returns_200(self, vs_client: TestClient) -> None:
        doc = _upload_pdf(vs_client)
        res = vs_client.post(
            f"/api/v1/documents/{doc['document_id']}/index"
            "?chunk_size=200&overlap=30&min_tokens=5",
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 200

    def test_index_response_shape(self, vs_client: TestClient) -> None:
        doc = _upload_pdf(vs_client)
        body = vs_client.post(
            f"/api/v1/documents/{doc['document_id']}/index"
            "?chunk_size=200&overlap=30&min_tokens=5",
            headers=GATEWAY_HEADERS,
        ).json()
        assert body["success"] is True
        assert body["document_id"] == doc["document_id"]
        assert body["filename"] == "handbook.pdf"
        assert "chunks_indexed" in body
        assert body["chunks_indexed"] > 0

    def test_index_unknown_document_returns_404(self, vs_client: TestClient) -> None:
        res = vs_client.post(
            "/api/v1/documents/00000000-0000-0000-0000-000000000000/index"
            "?chunk_size=200&overlap=30&min_tokens=5",
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 404

    def test_index_invalid_chunk_size_returns_422(self, vs_client: TestClient) -> None:
        doc = _upload_pdf(vs_client)
        res = vs_client.post(
            f"/api/v1/documents/{doc['document_id']}/index?chunk_size=5",
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 422

    def test_index_overlap_ge_chunk_size_returns_422(self, vs_client: TestClient) -> None:
        doc = _upload_pdf(vs_client)
        res = vs_client.post(
            f"/api/v1/documents/{doc['document_id']}/index"
            "?chunk_size=200&overlap=200",
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 422

    def test_index_requires_auth(self, vs_client: TestClient) -> None:
        doc = _upload_pdf(vs_client)
        res = vs_client.post(
            f"/api/v1/documents/{doc['document_id']}/index"
            "?chunk_size=200&overlap=30&min_tokens=5",
        )
        assert res.status_code == 401

    def test_reindex_does_not_create_duplicates(self, vs_client: TestClient) -> None:
        doc = _upload_pdf(vs_client)
        url = (
            f"/api/v1/documents/{doc['document_id']}/index"
            "?chunk_size=200&overlap=30&min_tokens=5&reindex=false"
        )
        r1 = vs_client.post(url, headers=GATEWAY_HEADERS).json()
        r2 = vs_client.post(
            url.replace("reindex=false", "reindex=true"),
            headers=GATEWAY_HEADERS,
        ).json()
        # reindex=true deletes old then inserts fresh → same count
        assert r1["chunks_indexed"] == r2["chunks_indexed"]


class TestHealthEndpoint:
    def test_health_returns_200(self, vs_client: TestClient) -> None:
        res = vs_client.get("/api/v1/vectorstore/health", headers=GATEWAY_HEADERS)
        assert res.status_code == 200

    def test_health_status_healthy(self, vs_client: TestClient) -> None:
        body = vs_client.get("/api/v1/vectorstore/health", headers=GATEWAY_HEADERS).json()
        assert body["status"] == "healthy"

    def test_health_has_required_fields(self, vs_client: TestClient) -> None:
        body = vs_client.get("/api/v1/vectorstore/health", headers=GATEWAY_HEADERS).json()
        assert "total_chunks" in body
        assert "unique_documents" in body
        assert "database" in body

    def test_health_requires_auth(self, vs_client: TestClient) -> None:
        res = vs_client.get("/api/v1/vectorstore/health")
        assert res.status_code == 401


class TestCountEndpoint:
    def test_count_returns_200(self, vs_client: TestClient) -> None:
        res = vs_client.get("/api/v1/vectorstore/count", headers=GATEWAY_HEADERS)
        assert res.status_code == 200

    def test_count_zero_when_empty(self, vs_client: TestClient) -> None:
        body = vs_client.get("/api/v1/vectorstore/count", headers=GATEWAY_HEADERS).json()
        assert body["total_chunks"] == 0
        assert body["unique_documents"] == 0

    def test_count_increases_after_index(self, vs_client: TestClient) -> None:
        doc = _upload_pdf(vs_client)
        vs_client.post(
            f"/api/v1/documents/{doc['document_id']}/index"
            "?chunk_size=200&overlap=30&min_tokens=5",
            headers=GATEWAY_HEADERS,
        )
        body = vs_client.get("/api/v1/vectorstore/count", headers=GATEWAY_HEADERS).json()
        assert body["total_chunks"] > 0
        assert body["unique_documents"] == 1

    def test_count_requires_auth(self, vs_client: TestClient) -> None:
        res = vs_client.get("/api/v1/vectorstore/count")
        assert res.status_code == 401
