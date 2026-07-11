"""Citation builder — produces traceable source references from search results.

Every answer the LLM generates must be traceable to a specific document,
page, and section.  This module extracts that information from the search
results and deduplicates it.

Usage::

    from app.retrieval.citation_builder import CitationBuilder
    citations = CitationBuilder().build(search_results)
"""
from __future__ import annotations

from app.models.retrieval_result import Citation
from app.models.search_result import SearchResult


class CitationBuilder:
    """Builds a deduplicated, ordered list of Citations from search results.

    Deduplication key: (filename, page, section).
    The first occurrence (highest rank = best score) wins.
    """

    def build(self, results: list[SearchResult]) -> list[Citation]:
        """Return one Citation per unique (filename, page, section) combination.

        Args:
            results: Reranked results, rank 0 first.

        Returns:
            Ordered list of Citation objects.
        """
        seen: set[tuple[str, int | None, str]] = set()
        citations: list[Citation] = []

        for r in results:
            key = (r.filename, r.page, r.section)
            if key in seen:
                continue
            seen.add(key)
            citations.append(
                Citation(
                    document=r.filename or "Unknown",
                    page=r.page if r.page and r.page > 0 else None,
                    section=r.section or "",
                    chunk_id=r.chunk_id,
                    score=round(r.score, 4),
                )
            )

        return citations
