"""Tests for the IT Agent node."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.it.it_agent import it_agent_node
from app.llm.llm_service import LLMService
from app.llm.providers.local_provider import LocalLLMProvider
from app.models.graph_state import GraphState
from app.models.retrieval_result import Citation
from app.tools.retrieval_tool import RetrievalResult, RetrievalTool


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _mock_retrieval(context: str = "Reset your password at it.acme.com.", chunks: int = 1) -> RetrievalTool:
    tool = MagicMock(spec=RetrievalTool)
    tool.run = AsyncMock(return_value=RetrievalResult(
        context=context,
        citations=[Citation(document="it_guide.pdf", page=1, section="Passwords", chunk_id="it1", score=0.91)],
        chunks_found=chunks,
    ))
    return tool


def _state(**overrides) -> GraphState:
    base: GraphState = {
        "question": "How do I reset my VPN password?",
        "messages": [],
        "top_k": 5,
        "min_score": 0.0,
        "department": None,
        "document_id": None,
        "errors": [],
        "metadata": {},
    }
    base.update(overrides)  # type: ignore[arg-type]
    return base


class TestITAgentNode:
    def test_returns_answer(self) -> None:
        tool = _mock_retrieval()
        llm = LLMService(provider=LocalLLMProvider())
        result = _run(it_agent_node(_state(), retrieval_tool=tool, llm_service=llm))
        assert "answer" in result
        assert len(result["answer"]) > 0

    def test_citations_returned(self) -> None:
        tool = _mock_retrieval()
        llm = LLMService(provider=LocalLLMProvider())
        result = _run(it_agent_node(_state(), retrieval_tool=tool, llm_service=llm))
        assert isinstance(result["citations"], list)

    def test_provider_is_local(self) -> None:
        tool = _mock_retrieval()
        llm = LLMService(provider=LocalLLMProvider())
        result = _run(it_agent_node(_state(), retrieval_tool=tool, llm_service=llm))
        assert result.get("provider") == "local"

    def test_chunks_found_in_metadata(self) -> None:
        tool = _mock_retrieval(chunks=3)
        llm = LLMService(provider=LocalLLMProvider())
        result = _run(it_agent_node(_state(), retrieval_tool=tool, llm_service=llm))
        assert result.get("metadata", {}).get("it_chunks_found") == 3

    def test_retrieval_error_returns_fallback(self) -> None:
        tool = MagicMock(spec=RetrievalTool)
        tool.run = AsyncMock(side_effect=RuntimeError("Chroma down"))
        llm = LLMService(provider=LocalLLMProvider())
        result = _run(it_agent_node(_state(), retrieval_tool=tool, llm_service=llm))
        assert result.get("answer")
        assert len(result.get("errors", [])) > 0

    def test_llm_error_returns_fallback(self) -> None:
        tool = _mock_retrieval()
        llm = LLMService(provider=LocalLLMProvider())
        with patch.object(llm, "complete", new=AsyncMock(side_effect=RuntimeError("LLM timeout"))):
            result = _run(it_agent_node(_state(), retrieval_tool=tool, llm_service=llm))
        assert result.get("answer")
        assert len(result.get("errors", [])) > 0

    def test_empty_context_no_crash(self) -> None:
        tool = _mock_retrieval(context="")
        llm = LLMService(provider=LocalLLMProvider())
        result = _run(it_agent_node(_state(), retrieval_tool=tool, llm_service=llm))
        assert "answer" in result

    def test_latency_recorded(self) -> None:
        tool = _mock_retrieval()
        llm = LLMService(provider=LocalLLMProvider())
        result = _run(it_agent_node(_state(), retrieval_tool=tool, llm_service=llm))
        assert result.get("latency_ms", -1) >= 0

    def test_token_counts_present(self) -> None:
        tool = _mock_retrieval()
        llm = LLMService(provider=LocalLLMProvider())
        result = _run(it_agent_node(_state(), retrieval_tool=tool, llm_service=llm))
        assert "prompt_tokens" in result
        assert "completion_tokens" in result
