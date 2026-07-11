"""HR Agent node — retrieves HR documents and generates a grounded answer."""
from __future__ import annotations

import time

from app.agents.hr.hr_prompt import hr_messages
from app.core.logging import get_logger
from app.llm.llm_service import LLMService
from app.models.graph_state import GraphState
from app.tools.citation_tool import citations_to_dicts
from app.tools.retrieval_tool import RetrievalTool

_log = get_logger()


async def hr_agent_node(
    state: GraphState,
    retrieval_tool: RetrievalTool,
    llm_service: LLMService,
) -> dict:
    """Execute the HR retrieval + generation pipeline.

    Steps:
      1. Call RetrievalTool to get context and citations.
      2. Build the HR Agent messages array.
      3. Call LLMService to generate the answer.
      4. Return updated GraphState fields.
    """
    question = state.get("question", "")
    history = state.get("messages", [])
    t0 = time.monotonic()

    # ── 1. Retrieve ────────────────────────────────────────────────────────────
    try:
        retrieval = await retrieval_tool.run(
            query=question,
            top_k=state.get("top_k", 5),
            min_score=state.get("min_score", 0.0),
            department=state.get("department"),
            document_id=state.get("document_id"),
        )
    except Exception as exc:
        _log.warning("hr_agent_retrieval_failed", error=str(exc))
        return {
            "answer": "I couldn't find that information in the uploaded HR documents.",
            "retrieved_context": "",
            "citations": [],
            "errors": [*state.get("errors", []), f"Retrieval error: {exc}"],
            "provider": "",
            "model": "",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": 0.0,
        }

    _log.info("hr_agent_retrieved", chunks=retrieval.chunks_found)

    # ── 2. Build messages ──────────────────────────────────────────────────────
    messages = hr_messages(
        context=retrieval.context,
        question=question,
        history=history,
    )

    # ── 3. Generate ────────────────────────────────────────────────────────────
    try:
        llm_resp = await llm_service.complete(messages)
    except Exception as exc:
        _log.warning("hr_agent_llm_failed", error=str(exc))
        return {
            "answer": "I'm sorry, I encountered an error while generating a response.",
            "retrieved_context": retrieval.context,
            "citations": citations_to_dicts(retrieval.citations),
            "errors": [*state.get("errors", []), f"LLM error: {exc}"],
            "provider": "",
            "model": "",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": round((time.monotonic() - t0) * 1000, 1),
        }

    total_latency = round((time.monotonic() - t0) * 1000, 1)
    _log.info(
        "hr_agent_complete",
        tokens=llm_resp.usage.total_tokens,
        latency_ms=total_latency,
    )

    return {
        "answer": llm_resp.content,
        "retrieved_context": retrieval.context,
        "citations": citations_to_dicts(retrieval.citations),
        "model": llm_resp.model,
        "provider": llm_resp.provider,
        "prompt_tokens": llm_resp.usage.prompt_tokens,
        "completion_tokens": llm_resp.usage.completion_tokens,
        "latency_ms": total_latency,
        "metadata": {
            **state.get("metadata", {}),
            "hr_chunks_found": retrieval.chunks_found,
        },
    }
