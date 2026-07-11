"""Search filter builder for ChromaDB where-clause construction.

ChromaDB uses a MongoDB-style filter dict for metadata filtering.
This module provides a clean API so callers don't need to know
ChromaDB's filter syntax.

Examples::

    filters = SearchFilters()
    filters.by_department("HR")
    filters.by_document("doc-uuid")
    where = filters.build()
    # → {"$and": [{"department": {"$eq": "HR"}}, {"document_id": {"$eq": "doc-uuid"}}]}
"""
from __future__ import annotations

from typing import Any


class SearchFilters:
    """Builder for ChromaDB ``where`` clause dicts.

    Usage::

        where = SearchFilters().by_department("HR").by_section("Leave Policy").build()
    """

    def __init__(self) -> None:
        self._clauses: list[dict[str, Any]] = []

    def by_document(self, document_id: str) -> "SearchFilters":
        self._clauses.append({"document_id": {"$eq": document_id}})
        return self

    def by_department(self, department: str) -> "SearchFilters":
        self._clauses.append({"department": {"$eq": department}})
        return self

    def by_section(self, section: str) -> "SearchFilters":
        self._clauses.append({"section": {"$eq": section}})
        return self

    def by_filename(self, filename: str) -> "SearchFilters":
        self._clauses.append({"filename": {"$eq": filename}})
        return self

    def by_category(self, category: str) -> "SearchFilters":
        self._clauses.append({"category": {"$eq": category}})
        return self

    def by_file_type(self, file_type: str) -> "SearchFilters":
        self._clauses.append({"file_type": {"$eq": file_type}})
        return self

    def build(self) -> dict[str, Any] | None:
        """Return the ChromaDB ``where`` dict, or ``None`` if no filters were set."""
        if not self._clauses:
            return None
        if len(self._clauses) == 1:
            return self._clauses[0]
        return {"$and": self._clauses}
