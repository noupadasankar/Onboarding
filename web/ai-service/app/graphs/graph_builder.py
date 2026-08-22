"""LangGraph graph builder — constructs and compiles the HR Onboarding workflow.

Architecture:
    onboarding_agent ──▶ END

Usage::

    graph = build_graph(vector_service=vs, llm_service=llm)
    result = await graph.ainvoke(state)
"""
from __future__ import annotations

from functools import partial

from langgraph.graph import END, StateGraph

from app.agents.onboarding.onboarding_agent import onboarding_agent_node
from app.graphs.nodes import fallback_node
from app.llm.llm_service import LLMService
from app.models.graph_state import GraphState
from app.services.vector_service import VectorService
from app.tools.retrieval_tool import RetrievalTool


def build_graph(
    vector_service: VectorService,
    llm_service: LLMService,
):
    """Compile and return the HR Onboarding LangGraph workflow.

    Node functions are partial-applied with their service dependencies so
    LangGraph receives plain ``(state) -> dict`` callables.

    Returns:
        A compiled LangGraph ``CompiledStateGraph`` ready for ``ainvoke()``.
    """
    retrieval_tool = RetrievalTool(vector_service=vector_service)

    # Bind service dependencies into each node via partial application.
    # LangGraph nodes must be plain (state) -> dict callables.
    _onboarding_agent = partial(onboarding_agent_node, retrieval_tool=retrieval_tool, llm_service=llm_service)

    builder: StateGraph = StateGraph(GraphState)

    # ── Nodes ──────────────────────────────────────────────────────────────────
    builder.add_node("onboarding_agent", _onboarding_agent)
    builder.add_node("fallback", fallback_node)

    # ── Entry point ────────────────────────────────────────────────────────────
    builder.set_entry_point("onboarding_agent")

    # ── Terminal edges ─────────────────────────────────────────────────────────
    builder.add_edge("onboarding_agent", END)
    builder.add_edge("fallback", END)

    return builder.compile()
