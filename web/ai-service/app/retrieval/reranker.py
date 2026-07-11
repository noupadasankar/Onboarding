"""Reranker — re-orders vector search results by relevance.

Phase 1 (this increment): score-based reranker using cosine similarity scores
already returned by ChromaDB.  No external model required.

Phase 2 (future): plug in a cross-encoder (Cohere Rerank, BAAI/bge-reranker,
or Voyage rerank-2) by subclassing BaseReranker and registering it in the
factory below.

Public API::

    reranker = ScoreReranker(top_k=5)
    top = reranker.rerank(search_results)
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.search_result import SearchResult


class BaseReranker(ABC):
    @abstractmethod
    def rerank(self, results: list[SearchResult]) -> list[SearchResult]:
        """Return a re-ordered (and possibly truncated) list of results."""


class ScoreReranker(BaseReranker):
    """Rerank by descending cosine similarity score, keep top_k.

    Args:
        top_k: Maximum number of results to keep after reranking.
        min_score: Discard results below this similarity threshold.
    """

    def __init__(self, top_k: int = 5, min_score: float = 0.0) -> None:
        self.top_k = top_k
        self.min_score = min_score

    def rerank(self, results: list[SearchResult]) -> list[SearchResult]:
        """Sort by score descending, filter by min_score, keep top_k."""
        filtered = [r for r in results if r.score >= self.min_score]
        sorted_results = sorted(filtered, key=lambda r: r.score, reverse=True)
        top = sorted_results[: self.top_k]
        # Re-assign rank
        for i, r in enumerate(top):
            r.rank = i
        return top


class DiversityReranker(BaseReranker):
    """Rerank ensuring no two consecutive results are from the same document.

    Useful to avoid the LLM being handed five chunks from the same page.
    Falls back to ScoreReranker ordering within each document group.

    Args:
        top_k: Maximum results to return.
        min_score: Discard results below this threshold.
    """

    def __init__(self, top_k: int = 5, min_score: float = 0.0) -> None:
        self.top_k = top_k
        self.min_score = min_score

    def rerank(self, results: list[SearchResult]) -> list[SearchResult]:
        filtered = sorted(
            [r for r in results if r.score >= self.min_score],
            key=lambda r: r.score,
            reverse=True,
        )
        seen_docs: set[str] = set()
        primary: list[SearchResult] = []
        secondary: list[SearchResult] = []

        for r in filtered:
            if r.document_id not in seen_docs:
                primary.append(r)
                seen_docs.add(r.document_id)
            else:
                secondary.append(r)

        merged = primary + secondary
        top = merged[: self.top_k]
        for i, r in enumerate(top):
            r.rank = i
        return top


def get_reranker(strategy: str = "score", top_k: int = 5, min_score: float = 0.0) -> BaseReranker:
    """Factory: return a reranker by strategy name."""
    if strategy == "diversity":
        return DiversityReranker(top_k=top_k, min_score=min_score)
    return ScoreReranker(top_k=top_k, min_score=min_score)
