"""Standalone (non-agent) graph nodes."""
from __future__ import annotations

from app.core.logging import get_logger
from app.models.graph_state import GraphState

_log = get_logger()

_FALLBACK_ANSWER = (
    "I'm sorry, I couldn't find a suitable agent to handle your request. "
    "This system currently handles HR-related questions. "
    "For Finance, IT, or other topics, please contact the relevant department."
)


async def fallback_node(state: GraphState) -> dict:
    """Handles requests that didn't match any known agent."""
    _log.info(
        "fallback_node_triggered",
        selected_agent=state.get("selected_agent", "none"),
        question=state.get("question", "")[:80],
    )
    return {
        "answer": _FALLBACK_ANSWER,
        "retrieved_context": "",
        "citations": [],
        "model": "",
        "provider": "",
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "latency_ms": 0.0,
    }
