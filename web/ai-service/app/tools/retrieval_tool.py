"""Retrieval tool — wraps the Increment 7 pipeline into a single callable.

HR Agent calls this instead of touching ChromaDB or EmbeddingPipeline directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.logging import get_logger
from app.models.retrieval_result import Citation
from app.retrieval.retrieval_pipeline import RetrievalPipeline
from app.retrieval.retrieval_service import RetrievalConfig, RetrievalService
from app.services.vector_service import VectorService

_log = get_logger()


@dataclass
class RetrievalResult:
    context: str
    citations: list[Citation]
    chunks_found: int


class RetrievalTool:
    """Single-responsibility wrapper around the RAG retrieval pipeline."""

    def __init__(self, vector_service: VectorService) -> None:
        self._vs = vector_service

    @property
    def vector_service(self) -> VectorService:
        return self._vs

    async def run(
        self,
        query: str,
        *,
        top_k: int = 5,
        min_score: float = 0.0,
        department: str | None = None,
        document_id: str | None = None,
        section: str | None = None,
    ) -> RetrievalResult:
        """Retrieve relevant chunks for *query* and return context + citations.

        Args:
            query: Normalised user question.
            top_k: Max chunks to return after reranking.
            min_score: Minimum similarity score threshold.
            department: Optional metadata filter.
            document_id: Optional restrict to one document.
            section: Optional section filter.

        Returns:
            RetrievalResult with context string, citations, and chunk count.
        """
        cfg = RetrievalConfig(
            top_k_search=20,
            top_k_rerank=top_k,
            min_score=min_score,
            department=department,
            document_id=document_id,
            section=section,
        )
        svc = RetrievalService(vector_service=self._vs)
        pipeline = RetrievalPipeline(service=svc)

        _log.info("retrieval_tool_run", query=query[:80], top_k=top_k)
        result = await pipeline.run(query, cfg)

        return RetrievalResult(
            context=result.context,
            citations=result.citations,
            chunks_found=result.chunks_found,
        )
