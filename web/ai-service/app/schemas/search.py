"""Request and response schemas for the /search endpoint."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.retrieval_result import Citation


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=1000, description="User question")
    department: str | None = Field(default=None, description="Filter by department")
    document_id: str | None = Field(default=None, description="Filter to a specific document")
    section: str | None = Field(default=None, description="Filter by section heading")
    top_k: int = Field(default=5, ge=1, le=20, description="Max chunks to return")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score")
    use_hybrid: bool = Field(
        default=True,
        description=(
            "Enable BM25 + dense hybrid search with Reciprocal Rank Fusion (RRF). "
            "Improves recall for exact identifiers (e.g. policy codes, amounts, brand names) "
            "that pure semantic search may rank poorly."
        ),
    )


class SearchResponse(BaseModel):
    query: str
    chunks_found: int
    context: str
    prompt: str
    citations: list[Citation] = []
    context_token_count: int = 0
