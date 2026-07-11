"""Citation model — a traceable reference to a source chunk."""
from __future__ import annotations

from pydantic import BaseModel


class Citation(BaseModel):
    """Traceable reference to a source document chunk."""

    document: str
    """Source filename (e.g. ``Employee_Handbook.pdf``)."""

    page: int | None = None
    section: str = ""
    chunk_id: str = ""
    score: float = 0.0
    """Similarity score of the chunk that produced this citation."""


class RetrievalResult(BaseModel):
    """Full output of the retrieval pipeline — everything needed by the LLM."""

    query: str
    """The normalised user query."""

    chunks_found: int
    """Number of chunks returned after reranking."""

    context: str
    """Assembled context text, ready to insert into the prompt."""

    prompt: str
    """Full structured prompt (system + context + question)."""

    citations: list[Citation] = []
    """Ordered list of traceable sources."""

    context_token_count: int = 0
    """Token count of the assembled context."""

    results: list = []
    """Raw SearchResult objects (list[SearchResult]), omitted from some responses."""
