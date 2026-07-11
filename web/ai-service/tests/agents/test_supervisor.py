"""Tests for supervisor routing logic."""
import asyncio

import pytest

from app.agents.supervisor.router import keyword_route, parse_routing_decision
from app.agents.supervisor.prompts import routing_messages, supervisor_system_prompt
from app.agents.supervisor.supervisor import supervisor_node
from app.llm.llm_service import LLMService
from app.llm.providers.local_provider import LocalLLMProvider
from app.models.graph_state import GraphState


# ── Router unit tests ──────────────────────────────────────────────────────────

class TestParseRoutingDecision:
    def test_exact_hr(self) -> None:
        assert parse_routing_decision("hr") == "hr"

    def test_exact_unknown(self) -> None:
        assert parse_routing_decision("unknown") == "hr"  # default to hr

    def test_hr_in_sentence(self) -> None:
        assert parse_routing_decision("The answer is hr agent.") == "hr"

    def test_whitespace_stripped(self) -> None:
        assert parse_routing_decision("  hr  ") == "hr"

    def test_fallback_on_garbage(self) -> None:
        assert parse_routing_decision("I don't know!!!") == "hr"

    def test_case_insensitive(self) -> None:
        assert parse_routing_decision("HR") == "hr"


class TestKeywordRoute:
    def test_leave_maps_to_hr(self) -> None:
        assert keyword_route("How many leave days?") == "hr"

    def test_holiday_maps_to_hr(self) -> None:
        assert keyword_route("What public holidays do we get?") == "hr"

    def test_handbook_maps_to_hr(self) -> None:
        assert keyword_route("Where is the employee handbook?") == "hr"

    def test_it_question_returns_none(self) -> None:
        assert keyword_route("Reset my VPN password") is None

    def test_generic_question_returns_none(self) -> None:
        assert keyword_route("What is the weather today?") is None

    def test_case_insensitive(self) -> None:
        assert keyword_route("ANNUAL LEAVE POLICY") == "hr"


class TestRoutingMessages:
    def test_returns_two_messages(self) -> None:
        msgs = routing_messages("leave days?", [])
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"

    def test_question_in_user_message(self) -> None:
        msgs = routing_messages("How many sick days?", [])
        assert "How many sick days?" in msgs[1]["content"]

    def test_history_included(self) -> None:
        history = [{"role": "user", "content": "leave?"}, {"role": "assistant", "content": "20 days."}]
        msgs = routing_messages("Can they be carried over?", history)
        assert "leave?" in msgs[1]["content"]


class TestSupervisorNode:
    def test_hr_keyword_fast_routes_to_hr(self) -> None:
        llm = LLMService(provider=LocalLLMProvider())
        state: GraphState = {
            "question": "How many annual leave days?",
            "messages": [],
            "errors": [],
            "metadata": {},
        }
        result = asyncio.get_event_loop().run_until_complete(
            supervisor_node(state, llm_service=llm)
        )
        assert result["selected_agent"] == "hr"

    def test_routing_metadata_set(self) -> None:
        llm = LLMService(provider=LocalLLMProvider())
        state: GraphState = {
            "question": "leave policy",
            "messages": [],
            "errors": [],
            "metadata": {},
        }
        result = asyncio.get_event_loop().run_until_complete(
            supervisor_node(state, llm_service=llm)
        )
        assert "routing_method" in result.get("metadata", {})

    def test_returns_dict_with_selected_agent(self) -> None:
        llm = LLMService(provider=LocalLLMProvider())
        state: GraphState = {
            "question": "employee handbook section on benefits",
            "messages": [],
            "errors": [],
            "metadata": {},
        }
        result = asyncio.get_event_loop().run_until_complete(
            supervisor_node(state, llm_service=llm)
        )
        assert "selected_agent" in result
