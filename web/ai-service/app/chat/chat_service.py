"""Chat service — orchestrates the full RAG + LLM pipeline.

Pipeline per request:
  1. Get or create conversation.
  2. Run retrieval pipeline (query → embed → search → rerank → context).
  3. Build messages array: system + history + [context + question].
  4. Call LLM (complete or stream).
  5. Append user + assistant messages to conversation.
  6. Persist conversation.
  7. Return formatted response.
"""
from __future__ import annotations

from app.chat.conversation_repository import ConversationRepository
from app.chat.conversation_service import ConversationService
from app.chat.response_formatter import format_response
from app.core.config import get_settings
from app.core.logging import get_logger
from app.llm.llm_service import LLMService
from app.models.retrieval_result import Citation
from app.retrieval.retrieval_pipeline import RetrievalPipeline
from app.retrieval.retrieval_service import RetrievalConfig
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.vector_service import VectorService

_log = get_logger()


class ChatService:
    """Orchestrates the full RAG + LLM pipeline for a single question.

    Args:
        vector_service: Used internally by RetrievalPipeline.
        llm_service: Configured LLM provider wrapper.
        conv_repo: Conversation persistence backend.
    """

    def __init__(
        self,
        vector_service: VectorService,
        llm_service: LLMService,
        conv_repo: ConversationRepository,
    ) -> None:
        self._vector_service = vector_service
        self._llm = llm_service
        self._conv_svc = ConversationService(conv_repo)

    async def chat(
        self,
        request: ChatRequest,
        user_id: str,
        tenant: str = "default",
    ) -> ChatResponse:
        s = get_settings()

        # ── 1. Conversation ───────────────────────────────────────────────────
        conv = self._conv_svc.get_or_create(
            conversation_id=request.conversation_id,
            user_id=user_id,
            tenant=tenant,
        )

        # ── 2. Retrieval ──────────────────────────────────────────────────────
        retrieval_cfg = RetrievalConfig(
            top_k_search=20,
            top_k_rerank=request.top_k,
            min_score=request.min_score,
            department=request.department,
            document_id=request.document_id,
        )
        from app.retrieval.retrieval_service import RetrievalService
        retrieval_svc = RetrievalService(vector_service=self._vector_service)
        pipeline = RetrievalPipeline(service=retrieval_svc)
        retrieval_result = await pipeline.run(request.question, retrieval_cfg)

        citations: list[Citation] = retrieval_result.citations

        # ── 3. Build messages ─────────────────────────────────────────────────
        history = conv.history_window(s.conversation_history_window)
        history_dicts = [{"role": m.role.value, "content": m.content} for m in history]

        from app.retrieval.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        base_messages = builder.build_messages(retrieval_result.context, request.question)
        # Insert history between system and user messages
        messages: list[dict[str, str]] = (
            [base_messages[0]]       # system
            + history_dicts          # prior turns
            + [base_messages[1]]     # current user message (with context)
        )

        # ── 4. Call LLM ───────────────────────────────────────────────────────
        llm_response = await self._llm.complete(messages)
        _log.info(
            "chat_llm_complete",
            conversation_id=conv.conversation_id,
            tokens=llm_response.usage.total_tokens,
            latency_ms=llm_response.latency_ms,
        )

        # ── 5 & 6. Persist conversation ───────────────────────────────────────
        conv.add_message("user", request.question)
        conv.add_message("assistant", llm_response.content)
        self._conv_svc.save(conv)

        # ── 7. Format response ────────────────────────────────────────────────
        return format_response(
            conversation_id=conv.conversation_id,
            llm_response=llm_response,
            citations=citations,
        )
