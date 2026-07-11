"""Integration tests for the POST /api/v1/search endpoint."""
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.retrieval_result import Citation, RetrievalResult
from app.retrieval.retrieval_pipeline import RetrievalPipeline
from app.services.vector_service import VectorService, get_vector_service
from app.repositories.vector_repository import VectorRepository
from app.vectorstore.chroma_client import ChromaClient
from tests.conftest import GATEWAY_HEADERS


def _sample_result(query: str = "How many leave days?") -> RetrievalResult:
    return RetrievalResult(
        query=query,
        chunks_found=3,
        context="Employees receive 20 days of annual leave per year.",
        prompt="You are OptiAgent...\n\nContext...\n\nQuestion: " + query,
        citations=[
            Citation(
                document="Employee_Handbook.pdf",
                page=24,
                section="Leave Policy",
                chunk_id="c1",
                score=0.92,
            )
        ],
        context_token_count=42,
        results=[],
    )


@pytest.fixture
def search_client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """TestClient with in-memory VectorService and a mocked RetrievalPipeline.

    The mock makes ``pipeline.run()`` return a canned result so tests
    exercise routing, auth, and schema validation — not the full pipeline.
    """
    # In-memory vector service for dependency injection
    mem_client = ChromaClient(mode="memory")
    repo = VectorRepository(client=mem_client, collection_name="test_search")
    vec_svc = VectorService(repo)

    # Mocked pipeline that returns a fixed result
    mock_pipeline = MagicMock(spec=RetrievalPipeline)
    mock_pipeline.run = AsyncMock(return_value=_sample_result())

    # Patch the class so the endpoint builds a mock instance
    monkeypatch.setattr("app.api.v1.search.RetrievalPipeline", lambda **kw: mock_pipeline)

    app = create_app()
    app.dependency_overrides[get_vector_service] = lambda: vec_svc

    with TestClient(app) as client:
        yield client


# ── Happy-path tests ───────────────────────────────────────────────────────────

class TestSearchEndpoint:
    def test_returns_200(self, search_client: TestClient) -> None:
        res = search_client.post(
            "/api/v1/search",
            json={"query": "How many leave days?"},
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 200

    def test_response_has_all_fields(self, search_client: TestClient) -> None:
        body = search_client.post(
            "/api/v1/search",
            json={"query": "How many leave days?"},
            headers=GATEWAY_HEADERS,
        ).json()
        for field in ("query", "chunks_found", "context", "prompt", "citations", "context_token_count"):
            assert field in body, f"Missing field: {field}"

    def test_query_echoed_in_response(self, search_client: TestClient) -> None:
        body = search_client.post(
            "/api/v1/search",
            json={"query": "How many leave days?"},
            headers=GATEWAY_HEADERS,
        ).json()
        assert body["query"] == "How many leave days?"

    def test_citations_is_list(self, search_client: TestClient) -> None:
        body = search_client.post(
            "/api/v1/search",
            json={"query": "leave policy"},
            headers=GATEWAY_HEADERS,
        ).json()
        assert isinstance(body["citations"], list)

    def test_citation_has_document_field(self, search_client: TestClient) -> None:
        body = search_client.post(
            "/api/v1/search",
            json={"query": "leave policy"},
            headers=GATEWAY_HEADERS,
        ).json()
        if body["citations"]:
            assert "document" in body["citations"][0]

    def test_optional_department_filter_accepted(self, search_client: TestClient) -> None:
        res = search_client.post(
            "/api/v1/search",
            json={"query": "leave policy", "department": "HR"},
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 200

    def test_optional_top_k_accepted(self, search_client: TestClient) -> None:
        res = search_client.post(
            "/api/v1/search",
            json={"query": "leave policy", "top_k": 10},
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 200

    def test_optional_min_score_accepted(self, search_client: TestClient) -> None:
        res = search_client.post(
            "/api/v1/search",
            json={"query": "leave policy", "min_score": 0.5},
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 200

    def test_context_token_count_is_int(self, search_client: TestClient) -> None:
        body = search_client.post(
            "/api/v1/search",
            json={"query": "leave policy"},
            headers=GATEWAY_HEADERS,
        ).json()
        assert isinstance(body["context_token_count"], int)


# ── Auth tests ─────────────────────────────────────────────────────────────────

class TestSearchAuth:
    def test_requires_auth_header(self, search_client: TestClient) -> None:
        res = search_client.post(
            "/api/v1/search",
            json={"query": "How many days?"},
        )
        assert res.status_code == 401

    def test_wrong_token_rejected(self, search_client: TestClient) -> None:
        res = search_client.post(
            "/api/v1/search",
            json={"query": "How many days?"},
            headers={**GATEWAY_HEADERS, "X-Internal-Token": "wrong-token"},
        )
        assert res.status_code == 401


# ── Validation tests ───────────────────────────────────────────────────────────

class TestSearchValidation:
    def test_empty_query_returns_422(self, search_client: TestClient) -> None:
        res = search_client.post(
            "/api/v1/search",
            json={"query": ""},
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 422

    def test_single_char_query_returns_422(self, search_client: TestClient) -> None:
        # min_length=2 in SearchRequest
        res = search_client.post(
            "/api/v1/search",
            json={"query": "x"},
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 422

    def test_top_k_above_max_returns_422(self, search_client: TestClient) -> None:
        res = search_client.post(
            "/api/v1/search",
            json={"query": "leave policy", "top_k": 999},
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 422

    def test_min_score_above_one_returns_422(self, search_client: TestClient) -> None:
        res = search_client.post(
            "/api/v1/search",
            json={"query": "leave policy", "min_score": 1.5},
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 422

    def test_missing_query_field_returns_422(self, search_client: TestClient) -> None:
        res = search_client.post(
            "/api/v1/search",
            json={},
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 422
