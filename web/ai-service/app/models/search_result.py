"""SearchResult model — a single chunk returned by vector search."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SearchResult(BaseModel):
    """One result from a ChromaDB similarity search."""

    chunk_id: str
    document_id: str
    text: str
    score: float
    """Cosine similarity in [0, 1] — higher is better."""

    rank: int = 0
    """Position after reranking (0-based)."""

    filename: str = ""
    page: int | None = None
    section: str = ""
    department: str = ""
    category: str = ""
    token_count: int = 0
    metadata: dict[str, Any] = {}
