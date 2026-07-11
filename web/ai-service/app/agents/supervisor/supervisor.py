"""Supervisor node — decides which agent handles the request."""
from __future__ import annotations

import time

from app.agents.supervisor.prompts import routing_messages
from app.agents.supervisor.router import keyword_route, parse_routing_decision
from app.core.logging import get_logger
from app.llm.llm_service import LLMService
from app.llm.providers.base_provider import LLMConfig
from app.models.graph_state import GraphState

_log = get_logger()


async def supervisor_node(
    state: GraphState,
    llm_service: LLMService,
) -> dict:
    """Determine which domain agent should handle *state['question']*.

    Strategy:
      1. Fast keyword pre-filter for obvious HR questions.
      2. LLM routing call for ambiguous questions.
      3. Fallback to "hr" on any error.

    Returns a partial GraphState dict with ``selected_agent`` set.
    """
    question = state.get("question", "")
    history = state.get("messages", [])
    t0 = time.monotonic()

    # Fast path — skip LLM call for clear HR keywords
    fast = keyword_route(question)
    if fast:
        _log.info("supervisor_fast_route", agent=fast, question=question[:80])
        return {
            "selected_agent": fast,
            "metadata": {**state.get("metadata", {}), "routing_method": "keyword"},
        }

    # LLM routing
    try:
        messages = routing_messages(question, history)
        resp = await llm_service.complete(
            messages,
            max_tokens=10,
            temperature=0.0,
        )
        agent = parse_routing_decision(resp.content)
        latency = round((time.monotonic() - t0) * 1000, 1)
        _log.info(
            "supervisor_llm_route",
            agent=agent,
            raw=resp.content[:40],
            latency_ms=latency,
        )
        return {
            "selected_agent": agent,
            "metadata": {
                **state.get("metadata", {}),
                "routing_method": "llm",
                "routing_latency_ms": latency,
            },
        }
    except Exception as exc:
        _log.warning("supervisor_routing_failed", error=str(exc))
        return {
            "selected_agent": "hr",
            "errors": [*state.get("errors", []), f"Supervisor routing error: {exc}"],
            "metadata": {**state.get("metadata", {}), "routing_method": "fallback"},
        }
