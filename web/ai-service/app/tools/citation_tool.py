"""Citation tool — serialises Citation objects to JSON-safe dicts for graph state."""
from __future__ import annotations

from app.models.retrieval_result import Citation


def citations_to_dicts(citations: list[Citation]) -> list[dict]:
    """Convert Citation objects to plain dicts for storage in GraphState."""
    return [
        {
            "document": c.document,
            "page": c.page,
            "section": c.section,
            "chunk_id": c.chunk_id,
            "score": round(c.score, 4),
        }
        for c in citations
    ]


def dicts_to_citations(dicts: list[dict]) -> list[Citation]:
    """Restore Citation objects from GraphState dicts."""
    return [Citation(**d) for d in dicts]
