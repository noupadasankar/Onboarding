"""API integration tests for POST /api/v1/chat."""
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.chat.chat_service import ChatService
from app.chat.conversation_repository import ConversationRepository, reset_conversation_repository
from app.llm.llm_service import LLMService
from app.llm.providers.local_provider import LocalLLMProvider
from app.main import create_app
from app.repositories.vector_repository import VectorRepository
from app.schemas.chat import ChatResponse, TokenUsageSchema
from app.services.vector_service import VectorService, get_vector_service
from app.vectorstore.chroma_client import ChromaClient
from tests.conftest import GATEWAY_HEADERS


def _canned_response() -> ChatResponse:
    return ChatResponse(
        conversation_id="test-conv-id-1234",
        answer="Employees receive 20 days of annual leave per year.",
        citations=[],
        model="local-mock-v1",
        provider="local",
        latency_ms=1.0,
        usage=TokenUsageSchema(prompt_tokens=100, completion_tokens=40, total_tokens=140),
    )


@pytest.fixture(autouse=True)
def _reset_conv_repo() -> Generator:
    reset_conversation_repository()
    yield
    reset_conversation_repository()


@pytest.fixture
def chat_client() -> Generator[TestClient, None, None]:
    """TestClient with mocked ChatService so no real LLM or Chroma calls occur."""
    mock_svc = MagicMock(spec=ChatService)
    mock_svc.chat = AsyncMock(return_value=_canned_response())
    mock_svc._vector_service = MagicMock()
    mock_svc._llm = MagicMock()

    from app.api.v1 import chat as chat_mod

    mem_client = ChromaClient(mode="memory")
    repo = VectorRepository(client=mem_client, collection_name="test_chat")
    vec_svc = VectorService(repo)

    app = create_app()
    app.dependency_overrides[get_vector_service] = lambda: vec_svc
    app.dependency_overrides[chat_mod._chat_service] = lambda: mock_svc

    with TestClient(app) as client:
        yield client


class TestChatEndpoint:
    def test_returns_200(self, chat_client: TestClient) -> None:
        res = chat_client.post(
            "/api/v1/chat",
            json={"question": "How many leave days?"},
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 200

    def test_response_has_answer(self, chat_client: TestClient) -> None:
        body = chat_client.post(
            "/api/v1/chat",
            json={"question": "How many leave days?"},
            headers=GATEWAY_HEADERS,
        ).json()
        assert "answer" in body
        assert len(body["answer"]) > 0

    def test_response_shape(self, chat_client: TestClient) -> None:
        body = chat_client.post(
            "/api/v1/chat",
            json={"question": "How many leave days?"},
            headers=GATEWAY_HEADERS,
        ).json()
        for field in ("conversation_id", "answer", "citations", "model", "provider", "usage"):
            assert field in body, f"Missing: {field}"

    def test_usage_fields(self, chat_client: TestClient) -> None:
        body = chat_client.post(
            "/api/v1/chat",
            json={"question": "leave days"},
            headers=GATEWAY_HEADERS,
        ).json()
        usage = body["usage"]
        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage
        assert "total_tokens" in usage

    def test_requires_auth(self, chat_client: TestClient) -> None:
        res = chat_client.post(
            "/api/v1/chat",
            json={"question": "leave days"},
        )
        assert res.status_code == 401

    def test_empty_question_returns_422(self, chat_client: TestClient) -> None:
        res = chat_client.post(
            "/api/v1/chat",
            json={"question": ""},
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 422

    def test_single_char_returns_422(self, chat_client: TestClient) -> None:
        res = chat_client.post(
            "/api/v1/chat",
            json={"question": "x"},
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 422

    def test_top_k_above_max_returns_422(self, chat_client: TestClient) -> None:
        res = chat_client.post(
            "/api/v1/chat",
            json={"question": "leave days", "top_k": 999},
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 422

    def test_conversation_id_optional(self, chat_client: TestClient) -> None:
        res = chat_client.post(
            "/api/v1/chat",
            json={"question": "leave days", "conversation_id": "some-id"},
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 200

    def test_department_filter_optional(self, chat_client: TestClient) -> None:
        res = chat_client.post(
            "/api/v1/chat",
            json={"question": "leave days", "department": "HR"},
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 200

    def test_wrong_token_returns_401(self, chat_client: TestClient) -> None:
        res = chat_client.post(
            "/api/v1/chat",
            json={"question": "leave days"},
            headers={**GATEWAY_HEADERS, "X-Internal-Token": "bad-token"},
        )
        assert res.status_code == 401
