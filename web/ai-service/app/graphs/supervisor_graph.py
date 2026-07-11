"""GraphRunner — converts a raw question into a ChatResponse via the graph.

The chat endpoint instantiates one GraphRunner per request (lightweight —
the compiled graph is rebuilt each time from injected services).

Design note: if per-request graph compilation becomes a bottleneck, cache
the compiled graph keyed by (vector_service_id, llm_provider_name).
"""
from __future__ import annotations

import time

from app.chat.conversation_repository import ConversationRepository
from app.chat.conversation_service import ConversationService
from app.core.config import get_settings
from app.core.logging import get_logger
from app.graphs.graph_builder import build_graph
from app.llm.llm_service import LLMService
from app.models.graph_state import GraphState
from app.models.retrieval_result import Citation
from app.schemas.chat import ChatRequest, ChatResponse, TokenUsageSchema
from app.services.vector_service import VectorService
from app.tools.citation_tool import dicts_to_citations

_log = get_logger()


class GraphRunner:
    """Wraps the compiled LangGraph workflow and exposes a single ``run()`` method."""

    def __init__(
        self,
        vector_service: VectorService,
        llm_service: LLMService,
        conv_repo: ConversationRepository,
    ) -> None:
        self._graph = build_graph(vector_service=vector_service, llm_service=llm_service)
        self._llm = llm_service
        self._conv_svc = ConversationService(conv_repo)
        self._vs = vector_service

    async def run(
        self,
        request: ChatRequest,
        user_id: str,
        tenant: str = "default",
    ) -> ChatResponse:
        s = get_settings()

        # Load or create conversation for history
        conv = self._conv_svc.get_or_create(
            conversation_id=request.conversation_id,
            user_id=user_id,
            tenant=tenant,
        )
        history = [
            {"role": m.role.value, "content": m.content}
            for m in conv.history_window(s.conversation_history_window)
        ]

        # Build initial state
        initial_state: GraphState = {
            "question": request.question,
            "user_id": user_id,
            "conversation_id": conv.conversation_id,
            "tenant": tenant,
            "department": request.department,
            "document_id": request.document_id,
            "top_k": request.top_k,
            "min_score": request.min_score,
            "selected_agent": "",
            "retrieved_context": "",
            "citations": [],
            "answer": "",
            "model": "",
            "provider": "",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": 0.0,
            "messages": history,
            "errors": [],
            "metadata": {},
        }

        t0 = time.monotonic()
        _log.info("graph_run_start", question=request.question[:80], user_id=user_id)

        final_state: GraphState = await self._graph.ainvoke(initial_state)

        total_ms = round((time.monotonic() - t0) * 1000, 1)
        _log.info(
            "graph_run_complete",
            agent=final_state.get("selected_agent"),
            tokens=final_state.get("prompt_tokens", 0) + final_state.get("completion_tokens", 0),
            latency_ms=total_ms,
            errors=final_state.get("errors", []),
        )

        # Persist conversation
        conv.add_message("user", request.question)
        conv.add_message("assistant", final_state.get("answer", ""))
        self._conv_svc.save(conv)

        citations: list[Citation] = dicts_to_citations(final_state.get("citations", []))
        prompt_t = final_state.get("prompt_tokens", 0)
        completion_t = final_state.get("completion_tokens", 0)

        return ChatResponse(
            conversation_id=conv.conversation_id,
            answer=final_state.get("answer", ""),
            citations=citations,
            model=final_state.get("model", ""),
            provider=final_state.get("provider", ""),
            latency_ms=total_ms,
            usage=TokenUsageSchema(
                prompt_tokens=prompt_t,
                completion_tokens=completion_t,
                total_tokens=prompt_t + completion_t,
            ),
        )
