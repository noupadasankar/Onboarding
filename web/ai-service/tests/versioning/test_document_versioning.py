"""AI-service vector-layer tests for document versioning.

Validates the contract the Node backend relies on:

  1. Upload + index doc_v1  → vectors exist in ChromaDB.
  2. DELETE /documents/{v1_id}/vectors  → vectors gone.
  3. Upload + index doc_v2  → only v2 vectors remain.

The Postgres side of versioning (SUPERSEDED status, isLatest flag,
parentDocumentId chain) is handled by the Node backend and is tested
separately in the Node test suite.  These tests validate the AI-service
DELETE endpoint that the Node backend calls as part of the supersede flow.

All tests use an isolated in-memory ChromaDB instance — no server required.
"""
from __future__ import annotations

import io
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.vector_repository import VectorRepository
from app.services.chunk_service import ChunkService, get_chunk_service
from app.services.document_service import DocumentService, get_document_service
from app.services.vector_service import VectorService, get_vector_service
from app.vectorstore.chroma_client import ChromaClient
from tests.conftest import GATEWAY_HEADERS
from tests.loaders.conftest import make_text_pdf

# ── Content ───────────────────────────────────────────────────────────────────

_V1_TEXT = (
    "Employee Handbook Version 1. "
    "Annual leave entitlement is 20 days per year. "
    "Policy code HR-204 applies to all permanent staff. "
    "Sick leave allowance is 5 days per calendar year. "
    "All policies effective from January 2025. "
    "Contact HR for queries regarding policy HR-204. "
) * 6

_V2_TEXT = (
    "Employee Handbook Version 2. "
    "Annual leave entitlement is now 25 days per year (updated 2026). "
    "Policy code HR-204 updated January 2026 — see appendix A. "
    "Sick leave increased to 10 days per calendar year. "
    "Mental health leave introduced: 3 days per year (policy TE-004). "
    "Hybrid working policy section 7.2 revised. "
) * 6


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def ver_client() -> Generator[TestClient, None, None]:
    """Fresh TestClient with a fully isolated in-memory VectorService.

    Each test function gets its own empty ChromaDB collection so tests
    are completely independent of execution order.
    """
    doc_svc = DocumentService()
    chunk_svc = ChunkService()
    mem_client = ChromaClient(mode="memory")
    repo = VectorRepository(client=mem_client, collection_name="test_versioning")
    vec_svc = VectorService(repo)

    app = create_app()
    app.dependency_overrides[get_document_service] = lambda: doc_svc
    app.dependency_overrides[get_chunk_service] = lambda: chunk_svc
    app.dependency_overrides[get_vector_service] = lambda: vec_svc

    with TestClient(app) as client:
        yield client


# ── Helpers ───────────────────────────────────────────────────────────────────

def _upload(client: TestClient, text: str, filename: str = "Employee_Handbook.pdf") -> str:
    """Upload a PDF generated from *text* and return its ``document_id``."""
    pdf = make_text_pdf(text, pages=2)
    res = client.post(
        "/api/v1/documents/upload",
        files={"file": (filename, io.BytesIO(pdf), "application/pdf")},
        headers=GATEWAY_HEADERS,
    )
    assert res.status_code == 201, f"Upload failed ({res.status_code}): {res.text}"
    return res.json()["document_id"]


def _index(client: TestClient, doc_id: str) -> int:
    """Run the index pipeline for *doc_id*.  Returns ``chunks_indexed``."""
    res = client.post(
        f"/api/v1/documents/{doc_id}/index"
        "?chunk_size=200&overlap=30&min_tokens=5",
        headers=GATEWAY_HEADERS,
    )
    assert res.status_code == 200, f"Index failed ({res.status_code}): {res.text}"
    return res.json()["chunks_indexed"]


def _delete_vectors(client: TestClient, doc_id: str) -> dict:
    """Call DELETE /documents/{doc_id}/vectors and return the response body."""
    res = client.delete(
        f"/api/v1/documents/{doc_id}/vectors",
        headers=GATEWAY_HEADERS,
    )
    assert res.status_code == 200, f"Delete failed ({res.status_code}): {res.text}"
    return res.json()


def _count(client: TestClient) -> tuple[int, int]:
    """Return (total_chunks, unique_documents) from the count endpoint."""
    body = client.get("/api/v1/vectorstore/count", headers=GATEWAY_HEADERS).json()
    return body["total_chunks"], body["unique_documents"]


# ── Unit tests: DELETE endpoint ───────────────────────────────────────────────

class TestDeleteVectorsEndpoint:
    """Tests for DELETE /api/v1/documents/{document_id}/vectors."""

    def test_returns_200(self, ver_client: TestClient) -> None:
        doc_id = _upload(ver_client, _V1_TEXT)
        _index(ver_client, doc_id)
        res = ver_client.delete(
            f"/api/v1/documents/{doc_id}/vectors",
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 200

    def test_response_has_correct_shape(self, ver_client: TestClient) -> None:
        doc_id = _upload(ver_client, _V1_TEXT)
        _index(ver_client, doc_id)
        body = _delete_vectors(ver_client, doc_id)
        assert "document_id" in body
        assert "vectors_deleted" in body

    def test_vectors_deleted_equals_indexed_count(self, ver_client: TestClient) -> None:
        doc_id = _upload(ver_client, _V1_TEXT)
        indexed = _index(ver_client, doc_id)
        body = _delete_vectors(ver_client, doc_id)
        assert body["vectors_deleted"] == indexed

    def test_document_id_echoed_in_response(self, ver_client: TestClient) -> None:
        doc_id = _upload(ver_client, _V1_TEXT)
        _index(ver_client, doc_id)
        body = _delete_vectors(ver_client, doc_id)
        assert body["document_id"] == doc_id

    def test_delete_nonexistent_returns_zero_not_error(self, ver_client: TestClient) -> None:
        """Deleting a document that has no vectors should return 0, not a 404."""
        body = ver_client.delete(
            "/api/v1/documents/00000000-0000-0000-0000-000000000000/vectors",
            headers=GATEWAY_HEADERS,
        ).json()
        assert body["vectors_deleted"] == 0

    def test_requires_auth(self, ver_client: TestClient) -> None:
        doc_id = _upload(ver_client, _V1_TEXT)
        _index(ver_client, doc_id)
        res = ver_client.delete(f"/api/v1/documents/{doc_id}/vectors")  # no headers
        assert res.status_code == 401

    def test_wrong_token_rejected(self, ver_client: TestClient) -> None:
        doc_id = _upload(ver_client, _V1_TEXT)
        _index(ver_client, doc_id)
        res = ver_client.delete(
            f"/api/v1/documents/{doc_id}/vectors",
            headers={**GATEWAY_HEADERS, "X-Internal-Token": "wrong-token"},
        )
        assert res.status_code == 401

    def test_chunks_absent_after_delete(self, ver_client: TestClient) -> None:
        """After deletion the chunk count for that document must be zero."""
        doc_id = _upload(ver_client, _V1_TEXT)
        _index(ver_client, doc_id)

        chunks_before, _ = _count(ver_client)
        assert chunks_before > 0, "Expected chunks to exist before delete"

        _delete_vectors(ver_client, doc_id)

        chunks_after, docs_after = _count(ver_client)
        assert chunks_after == 0
        assert docs_after == 0

    def test_double_delete_is_idempotent(self, ver_client: TestClient) -> None:
        """A second DELETE on the same document should succeed with 0 deletions."""
        doc_id = _upload(ver_client, _V1_TEXT)
        _index(ver_client, doc_id)

        first = _delete_vectors(ver_client, doc_id)
        assert first["vectors_deleted"] > 0

        second = _delete_vectors(ver_client, doc_id)
        assert second["vectors_deleted"] == 0  # nothing left to delete

    def test_delete_does_not_affect_other_documents(self, ver_client: TestClient) -> None:
        """Deleting doc A must not remove doc B's vectors."""
        doc_a = _upload(ver_client, _V1_TEXT, filename="handbook_a.pdf")
        doc_b = _upload(ver_client, _V2_TEXT, filename="handbook_b.pdf")
        a_count = _index(ver_client, doc_a)
        b_count = _index(ver_client, doc_b)

        total_before, _ = _count(ver_client)
        assert total_before == a_count + b_count

        _delete_vectors(ver_client, doc_a)

        total_after, docs_after = _count(ver_client)
        assert total_after == b_count   # only B remains
        assert docs_after == 1


# ── Integration test: full versioning cycle ────────────────────────────────────

class TestDocumentVersioningFlow:
    """End-to-end vector lifecycle that mirrors the Node backend supersede flow.

    Sequence:
      Node detects same-name upload → markSuperseded(v1) → deleteVectors(v1) → index(v2)

    These tests exercise each phase in isolation and then the full sequence.
    """

    def test_phase1_v1_indexed_successfully(self, ver_client: TestClient) -> None:
        """Phase 1: v1 upload → index produces > 0 chunks."""
        doc_v1 = _upload(ver_client, _V1_TEXT)
        chunks = _index(ver_client, doc_v1)
        assert chunks > 0

        total, docs = _count(ver_client)
        assert total == chunks
        assert docs == 1

    def test_phase2_v1_vectors_gone_after_delete(self, ver_client: TestClient) -> None:
        """Phase 2: after deleteVectors(v1), the store is empty."""
        doc_v1 = _upload(ver_client, _V1_TEXT)
        _index(ver_client, doc_v1)

        body = _delete_vectors(ver_client, doc_v1)
        assert body["vectors_deleted"] > 0

        total, docs = _count(ver_client)
        assert total == 0
        assert docs == 0

    def test_phase3_v2_indexed_after_v1_deleted(self, ver_client: TestClient) -> None:
        """Phase 3: v2 indexes cleanly after v1 vectors are gone."""
        # Delete v1 vectors first (simulate supersede flow)
        doc_v1 = _upload(ver_client, _V1_TEXT)
        _index(ver_client, doc_v1)
        _delete_vectors(ver_client, doc_v1)

        # Index v2
        doc_v2 = _upload(ver_client, _V2_TEXT)
        v2_chunks = _index(ver_client, doc_v2)
        assert v2_chunks > 0

    def test_full_cycle_only_v2_remains(self, ver_client: TestClient) -> None:
        """Complete versioning cycle: v1 indexed → v1 deleted → v2 indexed → only v2.

        This is the key test that validates the core versioning contract.
        """
        # ── Step 1: index v1 ─────────────────────────────────────────────────
        doc_v1 = _upload(ver_client, _V1_TEXT)
        v1_chunks = _index(ver_client, doc_v1)
        assert _count(ver_client) == (v1_chunks, 1)

        # ── Step 2: supersede v1 (delete its vectors) ─────────────────────────
        del_body = _delete_vectors(ver_client, doc_v1)
        assert del_body["vectors_deleted"] == v1_chunks
        assert _count(ver_client) == (0, 0)

        # ── Step 3: index v2 ─────────────────────────────────────────────────
        doc_v2 = _upload(ver_client, _V2_TEXT)
        v2_chunks = _index(ver_client, doc_v2)
        assert v2_chunks > 0

        # ── Verify: only v2 vectors in store ─────────────────────────────────
        total, docs = _count(ver_client)
        assert total == v2_chunks
        assert docs == 1                 # one document (v2), not two

    def test_without_delete_both_versions_accumulate(self, ver_client: TestClient) -> None:
        """Sanity: if supersede is NOT called, both versions coexist in the store.

        This confirms the DELETE endpoint is what separates the two states —
        without it, old chunks continue to appear in search results.
        """
        doc_v1 = _upload(ver_client, _V1_TEXT, filename="handbook_v1.pdf")
        doc_v2 = _upload(ver_client, _V2_TEXT, filename="handbook_v2.pdf")
        v1_chunks = _index(ver_client, doc_v1)
        v2_chunks = _index(ver_client, doc_v2)

        total, docs = _count(ver_client)
        assert total == v1_chunks + v2_chunks   # both present
        assert docs == 2                         # two distinct document IDs

    def test_v2_only_state_confirms_single_document(self, ver_client: TestClient) -> None:
        """After the versioning cycle, unique_documents == 1 (v2 only)."""
        # Cycle
        doc_v1 = _upload(ver_client, _V1_TEXT)
        _index(ver_client, doc_v1)
        _delete_vectors(ver_client, doc_v1)
        doc_v2 = _upload(ver_client, _V2_TEXT)
        _index(ver_client, doc_v2)

        _, docs = _count(ver_client)
        assert docs == 1

    def test_health_endpoint_shows_v2_after_cycle(self, ver_client: TestClient) -> None:
        """Vectorstore health endpoint reflects the post-cycle state correctly."""
        # Cycle
        doc_v1 = _upload(ver_client, _V1_TEXT)
        _index(ver_client, doc_v1)
        _delete_vectors(ver_client, doc_v1)
        doc_v2 = _upload(ver_client, _V2_TEXT)
        _index(ver_client, doc_v2)

        health = ver_client.get("/api/v1/vectorstore/health", headers=GATEWAY_HEADERS).json()
        assert health["status"] == "healthy"
        assert health["unique_documents"] == 1
        assert health["total_chunks"] > 0
