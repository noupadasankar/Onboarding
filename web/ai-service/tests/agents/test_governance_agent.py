"""Tests for the Governance Agent node."""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.governance.governance_agent import governance_node, _PASS_THROUGH_CONFIDENCE
from app.llm.llm_service import LLMService
from app.llm.providers.local_provider import LocalLLMProvider
from app.llm.providers.base_provider import LLMResponse
from app.llm.token_usage import TokenUsage
from app.models.graph_state import GraphState


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _llm_returning(json_payload: dict) -> LLMService:
    """Return an LLMService whose complete() yields a fixed JSON string."""
    llm = LLMService(provider=LocalLLMProvider())
    resp = LLMResponse(
        content=json.dumps(json_payload),
        model="local",
        provider="local",
        usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
    )
    llm.complete = AsyncMock(return_value=resp)
    return llm


def _state(**overrides) -> GraphState:
    base: GraphState = {
        "question": "How many leave days?",
        "retrieved_context": "Employees get 20 annual leave days.",
        "answer": "You get 20 annual leave days.",
        "metadata": {},
        "errors": [],
    }
    base.update(overrides)  # type: ignore[arg-type]
    return base


class TestGovernanceNodePassThrough:
    def test_grounded_answer_unchanged(self) -> None:
        llm = _llm_returning({"grounded": True, "confidence": 0.95, "issues": [], "revised_answer": None})
        result = _run(governance_node(_state(), llm_service=llm))
        assert "answer" not in result or result["answer"] == _state()["answer"]

    def test_metadata_records_grounded_true(self) -> None:
        llm = _llm_returning({"grounded": True, "confidence": 0.9, "issues": [], "revised_answer": None})
        result = _run(governance_node(_state(), llm_service=llm))
        assert result["metadata"]["governance_grounded"] is True

    def test_metadata_records_confidence(self) -> None:
        llm = _llm_returning({"grounded": True, "confidence": 0.87, "issues": [], "revised_answer": None})
        result = _run(governance_node(_state(), llm_service=llm))
        assert result["metadata"]["governance_confidence"] == pytest.approx(0.87)

    def test_empty_answer_skipped(self) -> None:
        llm = LLMService(provider=LocalLLMProvider())
        llm.complete = AsyncMock()  # should never be called
        result = _run(governance_node(_state(answer=""), llm_service=llm))
        assert result == {}
        llm.complete.assert_not_called()


class TestGovernanceNodeRevision:
    def test_low_confidence_triggers_revision(self) -> None:
        revised = "Based on the context, I cannot confirm the exact number."
        llm = _llm_returning({
            "grounded": True,
            "confidence": _PASS_THROUGH_CONFIDENCE - 0.1,
            "issues": [],
            "revised_answer": revised,
        })
        result = _run(governance_node(_state(), llm_service=llm))
        assert result.get("answer") == revised

    def test_not_grounded_triggers_revision(self) -> None:
        revised = "I could not find this in the uploaded documents."
        llm = _llm_returning({
            "grounded": False,
            "confidence": 0.9,
            "issues": ["claim unsupported"],
            "revised_answer": revised,
        })
        result = _run(governance_node(_state(), llm_service=llm))
        assert result.get("answer") == revised

    def test_not_grounded_no_revised_answer_keeps_original(self) -> None:
        llm = _llm_returning({
            "grounded": False,
            "confidence": 0.9,
            "issues": ["unsupported"],
            "revised_answer": None,
        })
        original_answer = _state()["answer"]
        result = _run(governance_node(_state(), llm_service=llm))
        # No revised answer provided → original must not be overwritten
        assert result.get("answer") is None or result.get("answer") == original_answer

    def test_issues_stored_in_metadata(self) -> None:
        issues = ["Cites wrong page", "Number not in context"]
        llm = _llm_returning({"grounded": False, "confidence": 0.3, "issues": issues, "revised_answer": "N/A"})
        result = _run(governance_node(_state(), llm_service=llm))
        assert result["metadata"]["governance_issues"] == issues


class TestGovernanceNodeErrorHandling:
    def test_json_parse_failure_passes_through(self) -> None:
        llm = LLMService(provider=LocalLLMProvider())
        bad_resp = LLMResponse(
            content="This is not JSON at all",
            model="local", provider="local",
            usage=TokenUsage(prompt_tokens=5, completion_tokens=5, total_tokens=10),
        )
        llm.complete = AsyncMock(return_value=bad_resp)
        result = _run(governance_node(_state(), llm_service=llm))
        # Parse failure should not raise; original answer untouched
        assert "governance_error" in result.get("metadata", {})

    def test_fenced_json_parsed_correctly(self) -> None:
        payload = {"grounded": True, "confidence": 0.92, "issues": [], "revised_answer": None}
        fenced = f"```json\n{json.dumps(payload)}\n```"
        llm = LLMService(provider=LocalLLMProvider())
        resp = LLMResponse(
            content=fenced, model="local", provider="local",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )
        llm.complete = AsyncMock(return_value=resp)
        result = _run(governance_node(_state(), llm_service=llm))
        assert result["metadata"]["governance_grounded"] is True

    def test_llm_exception_adds_error_to_state(self) -> None:
        llm = LLMService(provider=LocalLLMProvider())
        llm.complete = AsyncMock(side_effect=RuntimeError("Provider offline"))
        result = _run(governance_node(_state(), llm_service=llm))
        assert any("Governance" in e for e in result.get("errors", []))
