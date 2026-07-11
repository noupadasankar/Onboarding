"""Integration tests for the full LangGraph supervisor workflow."""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.chat.conversation_repository import ConversationRepository
from app.graphs.supervisor_graph import GraphRunner
from app.llm.llm_service import LLMService
from app.llm.providers.local_provider import LocalLLMProvider
from app.models.retrieval_result import Citation
from app.repositories.vector_repository import VectorRepository
from app.schemas.chat import ChatRequest
from app.services.vector_service import VectorService
from app.tools.retrieval_tool import RetrievalResult, RetrievalTool
from app.vectorstore.chroma_client import ChromaClient


def _make_runner(mock_retrieval_context: str = "Employees get 20 leave days.") -> GraphRunner:
    """GraphRunner with LocalLLMProvider and mocked retrieval."""
    mem_client = ChromaClient(mode="memory")
    repo = VectorRepository(client=mem_client, collection_name=f"test_{uuid.uuid4().hex[:6]}")
    vec_svc = VectorService(repo)
    llm = LLMService(provider=LocalLLMProvider())
    conv_repo = ConversationRepository()

    runner = GraphRunner(vector_service=vec_svc, llm_service=llm, conv_repo=conv_repo)

    # Patch the retrieval tool inside the compiled graph to skip real ChromaDB
    mock_rt = MagicMock(spec=RetrievalTool)
    mock_rt.run = AsyncMock(return_value=RetrievalResult(
        context=mock_retrieval_context,
        citations=[Citation(document="handbook.pdf", page=5, section="Leave", chunk_id="c1", score=0.9)],
        chunks_found=1,
    ))

    # Rebind the hr_agent node's retrieval_tool via graph_builder
    import app.graphs.graph_builder as gb
    from functools import partial
    from app.agents.hr.hr_agent import hr_agent_node
    from app.agents.supervisor.supervisor import supervisor_node

    runner._graph = _patch_graph(vec_svc, llm, mock_rt)
    return runner


def _patch_graph(vec_svc, llm, mock_rt):
    """Build graph with mocked retrieval tool."""
    from langgraph.graph import END, StateGraph
    from app.graphs.edges import route_after_supervisor
    from app.graphs.nodes import fallback_node
    from app.models.graph_state import GraphState
    from functools import partial

    builder = StateGraph(GraphState)
    builder.add_node("supervisor", partial(supervisor_node, llm_service=llm))
    builder.add_node("hr_agent", partial(hr_agent_node, retrieval_tool=mock_rt, llm_service=llm))
    builder.add_node("fallback", fallback_node)
    builder.set_entry_point("supervisor")
    builder.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {"hr_agent": "hr_agent", "fallback": "fallback"},
    )
    builder.add_edge("hr_agent", END)
    builder.add_edge("fallback", END)
    return builder.compile()


class TestGraphRunnerBasic:
    def test_returns_chat_response(self) -> None:
        runner = _make_runner()
        req = ChatRequest(question="How many annual leave days?")
        result = asyncio.get_event_loop().run_until_complete(
            runner.run(req, user_id="u1")
        )
        assert result.answer

    def test_conversation_id_is_uuid(self) -> None:
        runner = _make_runner()
        req = ChatRequest(question="leave days?")
        result = asyncio.get_event_loop().run_until_complete(
            runner.run(req, user_id="u1")
        )
        assert len(result.conversation_id) == 36

    def test_citations_returned(self) -> None:
        runner = _make_runner()
        req = ChatRequest(question="leave policy")
        result = asyncio.get_event_loop().run_until_complete(
            runner.run(req, user_id="u1")
        )
        assert isinstance(result.citations, list)

    def test_usage_populated(self) -> None:
        runner = _make_runner()
        req = ChatRequest(question="leave days")
        result = asyncio.get_event_loop().run_until_complete(
            runner.run(req, user_id="u1")
        )
        assert result.usage.total_tokens >= 0

    def test_conversation_continues_with_id(self) -> None:
        runner = _make_runner()
        req1 = ChatRequest(question="How many leave days?")
        r1 = asyncio.get_event_loop().run_until_complete(runner.run(req1, user_id="u1"))
        req2 = ChatRequest(question="Can they carry over?", conversation_id=r1.conversation_id)
        r2 = asyncio.get_event_loop().run_until_complete(runner.run(req2, user_id="u1"))
        assert r2.conversation_id == r1.conversation_id


class TestGraphFallback:
    def test_unknown_routes_to_fallback(self) -> None:
        """Force selected_agent='unknown' to trigger fallback node."""
        from app.graphs.nodes import fallback_node
        from app.models.graph_state import GraphState

        state: GraphState = {
            "question": "what is bitcoin",
            "selected_agent": "unknown",
            "messages": [],
            "errors": [],
            "metadata": {},
        }
        result = asyncio.get_event_loop().run_until_complete(fallback_node(state))
        assert "answer" in result
        assert len(result["answer"]) > 0

    def test_edge_routes_hr_to_hr_agent(self) -> None:
        from app.graphs.edges import route_after_supervisor
        state = {"selected_agent": "hr"}
        assert route_after_supervisor(state) == "hr_agent"

    def test_edge_routes_unknown_to_fallback(self) -> None:
        from app.graphs.edges import route_after_supervisor
        state = {"selected_agent": "unknown"}
        assert route_after_supervisor(state) == "fallback"

    def test_edge_routes_missing_to_fallback(self) -> None:
        from app.graphs.edges import route_after_supervisor
        state = {}
        assert route_after_supervisor(state) == "fallback"


class TestChatApiWithGraph:
    """End-to-end API tests using the LangGraph runner."""

    @pytest.fixture
    def api_client(self):
        from collections.abc import Generator
        from fastapi.testclient import TestClient
        from app.main import create_app
        from app.api.v1 import chat as chat_mod
        from tests.conftest import GATEWAY_HEADERS

        runner = _make_runner()
        app = create_app()
        app.dependency_overrides[chat_mod._graph_runner] = lambda: runner

        with TestClient(app) as client:
            yield client, GATEWAY_HEADERS

    def test_200_response(self, api_client) -> None:
        client, headers = api_client
        res = client.post("/api/v1/chat", json={"question": "How many leave days?"}, headers=headers)
        assert res.status_code == 200

    def test_response_has_answer(self, api_client) -> None:
        client, headers = api_client
        body = client.post("/api/v1/chat", json={"question": "leave days?"}, headers=headers).json()
        assert "answer" in body

    def test_401_without_token(self, api_client) -> None:
        client, _ = api_client
        res = client.post("/api/v1/chat", json={"question": "leave days?"})
        assert res.status_code == 401

    def test_422_on_empty_question(self, api_client) -> None:
        client, headers = api_client
        res = client.post("/api/v1/chat", json={"question": ""}, headers=headers)
        assert res.status_code == 422
