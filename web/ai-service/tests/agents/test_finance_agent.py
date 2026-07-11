"""Tests for the Finance Agent node."""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.finance.finance_agent import finance_agent_node
from app.llm.llm_service import LLMService
from app.llm.providers.local_provider import LocalLLMProvider
from app.models.graph_state import GraphState
from app.models.retrieval_result import Citation
from app.tools.retrieval_tool import RetrievalResult, RetrievalTool


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _mock_retrieval(context: str = "Expense limit is £500.", chunks: int = 2) -> RetrievalTool:
    tool = MagicMock(spec=RetrievalTool)
    tool.run = AsyncMock(return_value=RetrievalResult(
        context=context,
        citations=[Citation(document="expense_policy.pdf", page=2, section="Limits", chunk_id="f1", score=0.88)],
        chunks_found=chunks,
    ))
    return tool


def _state(**overrides) -> GraphState:
    base: GraphState = {
        "question": "What is the expense reimbursement limit?",
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


class TestFinanceAgentNode:
    def test_returns_answer(self) -> None:
        tool = _mock_retrieval()
        llm = LLMService(provider=LocalLLMProvider())
        result = _run(finance_agent_node(_state(), retrieval_tool=tool, llm_service=llm))
        assert "answer" in result
        assert len(result["answer"]) > 0

    def test_citations_returned(self) -> None:
        tool = _mock_retrieval()
        llm = LLMService(provider=LocalLLMProvider())
        result = _run(finance_agent_node(_state(), retrieval_tool=tool, llm_service=llm))
        assert isinstance(result["citations"], list)
        assert len(result["citations"]) > 0

    def test_model_and_provider_set(self) -> None:
        tool = _mock_retrieval()
        llm = LLMService(provider=LocalLLMProvider())
        result = _run(finance_agent_node(_state(), retrieval_tool=tool, llm_service=llm))
        assert result.get("model")
        assert result.get("provider") == "local"

    def test_chunks_found_in_metadata(self) -> None:
        tool = _mock_retrieval(chunks=4)
        llm = LLMService(provider=LocalLLMProvider())
        result = _run(finance_agent_node(_state(), retrieval_tool=tool, llm_service=llm))
        assert result.get("metadata", {}).get("finance_chunks_found") == 4

    def test_retrieval_error_returns_fallback(self) -> None:
        tool = MagicMock(spec=RetrievalTool)
        tool.run = AsyncMock(side_effect=RuntimeError("Chroma down"))
        llm = LLMService(provider=LocalLLMProvider())
        result = _run(finance_agent_node(_state(), retrieval_tool=tool, llm_service=llm))
        assert result.get("answer")
        assert len(result.get("errors", [])) > 0

    def test_llm_error_returns_fallback(self) -> None:
        tool = _mock_retrieval()
        from unittest.mock import patch
        llm = LLMService(provider=LocalLLMProvider())
        with patch.object(llm, "complete", new=AsyncMock(side_effect=RuntimeError("LLM down"))):
            result = _run(finance_agent_node(_state(), retrieval_tool=tool, llm_service=llm))
        assert result.get("answer")
        assert len(result.get("errors", [])) > 0

    def test_empty_context_still_answers(self) -> None:
        tool = _mock_retrieval(context="")
        llm = LLMService(provider=LocalLLMProvider())
        result = _run(finance_agent_node(_state(), retrieval_tool=tool, llm_service=llm))
        assert "answer" in result

    def test_latency_recorded(self) -> None:
        tool = _mock_retrieval()
        llm = LLMService(provider=LocalLLMProvider())
        result = _run(finance_agent_node(_state(), retrieval_tool=tool, llm_service=llm))
        assert result.get("latency_ms", -1) >= 0

    def test_token_counts_returned(self) -> None:
        tool = _mock_retrieval()
        llm = LLMService(provider=LocalLLMProvider())
        result = _run(finance_agent_node(_state(), retrieval_tool=tool, llm_service=llm))
        assert "prompt_tokens" in result
        assert "completion_tokens" in result

    def test_history_passed_through(self) -> None:
        """History messages must not cause errors even if provided."""
        tool = _mock_retrieval()
        llm = LLMService(provider=LocalLLMProvider())
        history = [
            {"role": "user", "content": "Can I claim food?"},
            {"role": "assistant", "content": "Yes, within limits."},
        ]
        result = _run(finance_agent_node(_state(messages=history), retrieval_tool=tool, llm_service=llm))
        assert result.get("answer")
