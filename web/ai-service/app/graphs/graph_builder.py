"""LangGraph graph builder — constructs and compiles the full multi-agent workflow.

Architecture:
    supervisor ──▶ hr_agent ──▶ governance ──▶ END
                ├─▶ finance_agent ──▶ governance ──▶ END
                ├─▶ it_agent ──▶ governance ──▶ END
                └─▶ fallback ──▶ END

Usage::

    graph = build_graph(vector_service=vs, llm_service=llm)
    result = await graph.ainvoke(state)
"""
from __future__ import annotations

from functools import partial

from langgraph.graph import END, StateGraph

from app.agents.finance.finance_agent import finance_agent_node
from app.agents.governance.governance_agent import governance_node
from app.agents.hr.hr_agent import hr_agent_node
from app.agents.it.it_agent import it_agent_node
from app.agents.supervisor.supervisor import supervisor_node
from app.graphs.edges import route_after_domain_agent, route_after_supervisor
from app.graphs.nodes import fallback_node
from app.llm.llm_service import LLMService
from app.models.graph_state import GraphState
from app.services.vector_service import VectorService
from app.tools.retrieval_tool import RetrievalTool


def build_graph(
    vector_service: VectorService,
    llm_service: LLMService,
):
    """Compile and return the multi-agent supervisor LangGraph workflow.

    Node functions are partial-applied with their service dependencies so
    LangGraph receives plain ``(state) -> dict`` callables.

    Returns:
        A compiled LangGraph ``CompiledStateGraph`` ready for ``ainvoke()``.
    """
    retrieval_tool = RetrievalTool(vector_service=vector_service)

    # Bind service dependencies into each node via partial application.
    # LangGraph nodes must be plain (state) -> dict callables.
    _supervisor = partial(supervisor_node, llm_service=llm_service)
    _hr_agent = partial(hr_agent_node, retrieval_tool=retrieval_tool, llm_service=llm_service)
    _finance_agent = partial(finance_agent_node, retrieval_tool=retrieval_tool, llm_service=llm_service)
    _it_agent = partial(it_agent_node, retrieval_tool=retrieval_tool, llm_service=llm_service)
    _governance = partial(governance_node, llm_service=llm_service)

    builder: StateGraph = StateGraph(GraphState)

    # ── Nodes ──────────────────────────────────────────────────────────────────
    builder.add_node("supervisor", _supervisor)
    builder.add_node("hr_agent", _hr_agent)
    builder.add_node("finance_agent", _finance_agent)
    builder.add_node("it_agent", _it_agent)
    builder.add_node("governance", _governance)
    builder.add_node("fallback", fallback_node)

    # ── Entry point ────────────────────────────────────────────────────────────
    builder.set_entry_point("supervisor")

    # ── Supervisor → domain agents (conditional routing) ───────────────────────
    builder.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "hr_agent": "hr_agent",
            "finance_agent": "finance_agent",
            "it_agent": "it_agent",
            "fallback": "fallback",
        },
    )

    # ── Domain agents → governance (if answer produced) or END ─────────────────
    _domain_exits = {"governance": "governance", "__end__": END}
    builder.add_conditional_edges("hr_agent", route_after_domain_agent, _domain_exits)
    builder.add_conditional_edges("finance_agent", route_after_domain_agent, _domain_exits)
    builder.add_conditional_edges("it_agent", route_after_domain_agent, _domain_exits)

    # ── Terminal edges ─────────────────────────────────────────────────────────
    builder.add_edge("governance", END)
    builder.add_edge("fallback", END)

    return builder.compile()
