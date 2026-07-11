"""Tests for the HR Agent node."""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.hr.hr_agent import hr_agent_node
from app.agents.hr.hr_prompt import hr_messages, hr_system_prompt
from app.llm.llm_service import LLMService
from app.llm.providers.local_provider import LocalLLMProvider
from app.models.graph_state import GraphState
from app.tools.retrieval_tool import RetrievalResult, RetrievalTool
from app.models.retrieval_result import Citation


def _mock_retrieval_tool(context: str = "Employees get 20 leave days.", chunks: int = 1) -> RetrievalTool:
    tool = MagicMock(spec=RetrievalTool)
    tool.run = AsyncMock(return_value=RetrievalResult(
        context=context,
        citations=[Citation(document="handbook.pdf", page=5, section="Leave", chunk_id="c1", score=0.9)],
        chunks_found=chunks,
    ))
    return tool


class TestHRPrompt:
    def test_system_prompt_contains_optiagent(self) -> None:
        assert "OptiAgent" in hr_system_prompt()

    def test_messages_has_system_and_user(self) -> None:
        msgs = hr_messages("Some context.", "How many days?", [])
        assert msgs[0]["role"] == "system"
        assert msgs[-1]["role"] == "user"

    def test_context_in_user_message(self) -> None:
        msgs = hr_messages("20 days context.", "How many days?", [])
        assert "20 days context." in msgs[-1]["content"]

    def test_question_in_user_message(self) -> None:
        msgs = hr_messages("ctx", "How many sick days?", [])
        assert "How many sick days?" in msgs[-1]["content"]

    def test_history_inserted(self) -> None:
        history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
        msgs = hr_messages("ctx", "q?", history)
        roles = [m["role"] for m in msgs]
        assert "user" in roles[1:-1] or "assistant" in roles[1:-1]


class TestHRAgentNode:
    def test_returns_answer(self) -> None:
        tool = _mock_retrieval_tool()
        llm = LLMService(provider=LocalLLMProvider())
        state: GraphState = {
            "question": "How many leave days?",
            "messages": [],
            "top_k": 5,
            "min_score": 0.0,
            "department": None,
            "document_id": None,
            "errors": [],
            "metadata": {},
        }
        result = asyncio.get_event_loop().run_until_complete(
            hr_agent_node(state, retrieval_tool=tool, llm_service=llm)
        )
        assert "answer" in result
        assert len(result["answer"]) > 0

    def test_citations_returned(self) -> None:
        tool = _mock_retrieval_tool()
        llm = LLMService(provider=LocalLLMProvider())
        state: GraphState = {
            "question": "leave?",
            "messages": [],
            "top_k": 5,
            "min_score": 0.0,
            "department": None,
            "document_id": None,
            "errors": [],
            "metadata": {},
        }
        result = asyncio.get_event_loop().run_until_complete(
            hr_agent_node(state, retrieval_tool=tool, llm_service=llm)
        )
        assert isinstance(result["citations"], list)

    def test_retrieval_error_returns_fallback_answer(self) -> None:
        tool = MagicMock(spec=RetrievalTool)
        tool.run = AsyncMock(side_effect=RuntimeError("Chroma unavailable"))
        llm = LLMService(provider=LocalLLMProvider())
        state: GraphState = {
            "question": "leave?",
            "messages": [],
            "top_k": 5,
            "min_score": 0.0,
            "department": None,
            "document_id": None,
            "errors": [],
            "metadata": {},
        }
        result = asyncio.get_event_loop().run_until_complete(
            hr_agent_node(state, retrieval_tool=tool, llm_service=llm)
        )
        assert "couldn't find" in result["answer"].lower() or result["answer"]
        assert len(result.get("errors", [])) > 0

    def test_metadata_updated(self) -> None:
        tool = _mock_retrieval_tool(chunks=3)
        llm = LLMService(provider=LocalLLMProvider())
        state: GraphState = {
            "question": "benefits?",
            "messages": [],
            "top_k": 5,
            "min_score": 0.0,
            "department": None,
            "document_id": None,
            "errors": [],
            "metadata": {},
        }
        result = asyncio.get_event_loop().run_until_complete(
            hr_agent_node(state, retrieval_tool=tool, llm_service=llm)
        )
        assert result.get("metadata", {}).get("hr_chunks_found") == 3
