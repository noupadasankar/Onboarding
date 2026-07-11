"""Finance Agent — retrieval + generation for finance documents."""
from __future__ import annotations

import time
from pathlib import Path

from app.core.logging import get_logger
from app.llm.llm_service import LLMService
from app.models.graph_state import GraphState
from app.tools.citation_tool import citations_to_dicts
from app.tools.retrieval_tool import RetrievalTool

_log = get_logger()
_SYSTEM = (Path(__file__).parent.parent.parent / "prompts" / "finance_system.md").read_text(encoding="utf-8")


def _build_messages(context: str, question: str, history: list[dict]) -> list[dict]:
    ctx = context.strip() or "(No relevant Finance documents were found.)"
    user_content = f"### Context\n\n{ctx}\n\n### Question\n\n{question}"
    return [{"role": "system", "content": _SYSTEM}] + history[-10:] + [{"role": "user", "content": user_content}]


async def finance_agent_node(state: GraphState, retrieval_tool: RetrievalTool, llm_service: LLMService) -> dict:
    question = state.get("question", "")
    history = state.get("messages", [])
    t0 = time.monotonic()

    try:
        retrieval = await retrieval_tool.run(
            query=question, top_k=state.get("top_k", 5),
            min_score=state.get("min_score", 0.0),
            department=state.get("department"), document_id=state.get("document_id"),
        )
    except Exception as exc:
        _log.warning("finance_agent_retrieval_failed", error=str(exc))
        return {
            "answer": "I couldn't find that information in the uploaded Finance documents.",
            "retrieved_context": "", "citations": [],
            "errors": [*state.get("errors", []), f"Finance retrieval error: {exc}"],
            "provider": "", "model": "", "prompt_tokens": 0, "completion_tokens": 0, "latency_ms": 0.0,
        }

    try:
        llm_resp = await llm_service.complete(_build_messages(retrieval.context, question, history))
    except Exception as exc:
        _log.warning("finance_agent_llm_failed", error=str(exc))
        return {
            "answer": "I encountered an error generating a Finance response.",
            "retrieved_context": retrieval.context, "citations": citations_to_dicts(retrieval.citations),
            "errors": [*state.get("errors", []), f"Finance LLM error: {exc}"],
            "provider": "", "model": "", "prompt_tokens": 0, "completion_tokens": 0,
            "latency_ms": round((time.monotonic() - t0) * 1000, 1),
        }

    latency = round((time.monotonic() - t0) * 1000, 1)
    _log.info("finance_agent_complete", tokens=llm_resp.usage.total_tokens, latency_ms=latency)
    return {
        "answer": llm_resp.content, "retrieved_context": retrieval.context,
        "citations": citations_to_dicts(retrieval.citations),
        "model": llm_resp.model, "provider": llm_resp.provider,
        "prompt_tokens": llm_resp.usage.prompt_tokens, "completion_tokens": llm_resp.usage.completion_tokens,
        "latency_ms": latency,
        "metadata": {**state.get("metadata", {}), "finance_chunks_found": retrieval.chunks_found},
    }
