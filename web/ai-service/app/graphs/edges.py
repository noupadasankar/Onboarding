"""LangGraph conditional edge functions."""
from __future__ import annotations

from app.models.graph_state import GraphState


def route_after_supervisor(state: GraphState) -> str:
    """Return the next node name based on the supervisor's routing decision.

    Maps selected_agent values to node names registered in the graph.
    Unknown agents fall through to the fallback node.
    """
    agent = state.get("selected_agent", "unknown")
    if agent == "hr":
        return "hr_agent"
    if agent == "finance":
        return "finance_agent"
    if agent == "it":
        return "it_agent"
    return "fallback"


def route_after_domain_agent(state: GraphState) -> str:
    """Route to governance validation if an answer was produced, else END.

    This allows governance to run after any domain agent without wiring
    each agent to governance individually.
    """
    if state.get("answer"):
        return "governance"
    return "__end__"
