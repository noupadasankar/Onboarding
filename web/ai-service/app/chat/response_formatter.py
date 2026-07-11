"""Formats raw LLM + retrieval results into the public ChatResponse shape."""
from __future__ import annotations

from app.llm.providers.base_provider import LLMResponse
from app.models.retrieval_result import Citation
from app.schemas.chat import ChatResponse, TokenUsageSchema


def format_response(
    conversation_id: str,
    llm_response: LLMResponse,
    citations: list[Citation],
) -> ChatResponse:
    return ChatResponse(
        conversation_id=conversation_id,
        answer=llm_response.content,
        citations=citations,
        model=llm_response.model,
        provider=llm_response.provider,
        latency_ms=round(llm_response.latency_ms, 2),
        usage=TokenUsageSchema(
            prompt_tokens=llm_response.usage.prompt_tokens,
            completion_tokens=llm_response.usage.completion_tokens,
            total_tokens=llm_response.usage.total_tokens,
            estimated_cost_usd=llm_response.usage.estimated_cost_usd,
        ),
    )
