"""Request and response schemas for POST /api/v1/chat."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.retrieval_result import Citation


class TokenUsageSchema(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=4096, description="User question")
    conversation_id: str | None = Field(default=None, description="Resume an existing conversation")
    department: str | None = Field(default=None, description="Restrict retrieval to a department")
    document_id: str | None = Field(default=None, description="Restrict retrieval to one document")
    top_k: int = Field(default=5, ge=1, le=20, description="Max chunks to retrieve")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score")
    stream: bool = Field(default=False, description="Use SSE streaming response")


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    citations: list[Citation] = []
    model: str
    provider: str
    latency_ms: float = 0.0
    usage: TokenUsageSchema = Field(default_factory=TokenUsageSchema)
