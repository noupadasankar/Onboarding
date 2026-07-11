"""Retrieval service — orchestrates the full query-to-prompt pipeline.

Steps:
  1.  Normalise query (QueryProcessor).
  2.  Embed query (EmbeddingPipeline / LocalProvider).
  3.  Search ChromaDB (VectorService).
  4.  Map raw results to SearchResult objects.
  5.  Rerank (ScoreReranker / DiversityReranker).
  6.  Build context within token budget (ContextBuilder).
  7.  Build citations (CitationBuilder).
  8.  Build prompt (PromptBuilder).
  9.  Return RetrievalResult.

No LLM call happens here. That is Increment 8.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.logging import get_logger
from app.embeddings.embedding_pipeline import EmbeddingPipeline
from app.embeddings.embedding_service import EmbeddingConfig
from app.models.retrieval_result import RetrievalResult
from app.models.search_result import SearchResult
from app.models.vector_document import VectorSearchResult
from app.retrieval.citation_builder import CitationBuilder
from app.retrieval.context_builder import ContextBuilder
from app.retrieval.prompt_builder import PromptBuilder
from app.retrieval.query_processor import QueryProcessor
from app.retrieval.reranker import BaseReranker, ScoreReranker
from app.services.vector_service import VectorService
from app.vectorstore.search_filters import SearchFilters

_log = get_logger()


@dataclass
class RetrievalConfig:
    """Configuration for a retrieval run."""

    top_k_search: int = 20
    """Number of results requested from ChromaDB."""

    top_k_rerank: int = 5
    """Number of results kept after reranking."""

    min_score: float = 0.0
    """Minimum similarity score to include a result."""

    max_context_tokens: int = 6_000
    """Token budget for the assembled context."""

    department: str | None = None
    """Optional metadata filter — restrict to a department."""

    document_id: str | None = None
    """Optional metadata filter — restrict to one document."""

    section: str | None = None
    """Optional metadata filter — restrict to one section."""

    rerank_strategy: str = "score"
    """Reranker strategy: ``"score"`` (default) or ``"diversity"``."""

    use_hybrid: bool = True
    """Enable BM25 + dense hybrid search with Reciprocal Rank Fusion (RRF).

    When True, the dense results are fused with BM25 keyword results before
    reranking.  This improves recall for exact identifiers (e.g. "HR-204",
    "£150", "BUPA") that pure semantic search may miss.
    Gracefully degrades to dense-only if ``rank_bm25`` is not installed.
    """


def _map_result(vsr: VectorSearchResult) -> SearchResult:
    """Convert VectorSearchResult (from Increment 6) to SearchResult."""
    meta = vsr.metadata or {}
    page_raw = meta.get("page", None)
    page = int(page_raw) if page_raw is not None and str(page_raw).lstrip("-").isdigit() else None
    if page is not None and page < 0:
        page = None

    return SearchResult(
        chunk_id=vsr.chunk_id,
        document_id=vsr.document_id,
        text=vsr.text,
        score=vsr.score,
        filename=str(meta.get("filename", "")),
        page=page,
        section=str(meta.get("section", "") or ""),
        department=str(meta.get("department", "")),
        category=str(meta.get("category", "")),
        token_count=int(meta.get("token_count", 0)),
        metadata=meta,
    )


class RetrievalService:
    """Runs the full retrieval pipeline.

    Args:
        vector_service: For semantic search.
        embedding_pipeline: For embedding the query.
        reranker: Reranker implementation. Defaults to ScoreReranker.
        context_builder: Assembles context text. Defaults to ContextBuilder.
        prompt_builder: Builds the final prompt. Defaults to PromptBuilder.
        citation_builder: Builds citations. Defaults to CitationBuilder.
        query_processor: Normalises raw queries. Defaults to QueryProcessor.
    """

    def __init__(
        self,
        vector_service: VectorService,
        embedding_pipeline: EmbeddingPipeline | None = None,
        reranker: BaseReranker | None = None,
        context_builder: ContextBuilder | None = None,
        prompt_builder: PromptBuilder | None = None,
        citation_builder: CitationBuilder | None = None,
        query_processor: QueryProcessor | None = None,
    ) -> None:
        self._vs = vector_service
        self._embed = embedding_pipeline or EmbeddingPipeline()
        self._reranker: BaseReranker = reranker or ScoreReranker()
        self._ctx = context_builder or ContextBuilder()
        self._prompt = prompt_builder or PromptBuilder()
        self._cite = citation_builder or CitationBuilder()
        self._qp = query_processor or QueryProcessor()

    async def retrieve(
        self,
        raw_query: str,
        config: RetrievalConfig | None = None,
    ) -> RetrievalResult:
        """Run the full retrieval pipeline.

        Args:
            raw_query: Raw user question string.
            config: Optional per-request configuration overrides.

        Returns:
            RetrievalResult with context, prompt, and citations.
        """
        cfg = config or RetrievalConfig()

        # ── 1. Normalise ──────────────────────────────────────────────────────
        query = self._qp.process(raw_query)
        _log.info("retrieval_query_normalised", query=query)

        # ── 2. Embed query ────────────────────────────────────────────────────
        from app.models.chunk import Chunk
        from app.models.document import FileType
        import uuid

        # Build a minimal synthetic Chunk so EmbeddingPipeline can embed the query
        query_chunk = Chunk(
            chunk_id=f"query_{uuid.uuid4().hex[:8]}",
            document_id="query",
            chunk_index=0,
            text=query,
            token_count=0,
            metadata={},
        )
        embedded = await self._embed.run(
            [query_chunk],
            document_filename="query",
        )

        if not embedded:
            _log.warning("retrieval_embedding_failed", query=query)
            return self._empty_result(query)

        query_vector = embedded[0].embedding

        # ── 3. Semantic search ────────────────────────────────────────────────
        sf = SearchFilters()
        if cfg.department:
            sf.by_department(cfg.department)
        if cfg.document_id:
            sf.by_document(cfg.document_id)
        if cfg.section:
            sf.by_section(cfg.section)
        where = sf.build()

        raw_results: list[VectorSearchResult] = self._vs.search(
            query_embedding=query_vector,
            n_results=cfg.top_k_search,
            department=cfg.department,
            document_id=cfg.document_id,
        )
        _log.info("retrieval_search_complete", raw_count=len(raw_results))

        if not raw_results:
            return self._empty_result(query)

        # ── 3b. Hybrid fusion (BM25 + dense RRF) ─────────────────────────────
        if cfg.use_hybrid:
            from app.retrieval.hybrid_retriever import HybridRetriever
            hybrid = HybridRetriever(vector_service=self._vs)
            raw_results = hybrid.retrieve(
                query_text=query,
                dense_results=raw_results,
                department=cfg.department,
                n_results=cfg.top_k_search,
            )
            _log.info("retrieval_hybrid_complete", fused_count=len(raw_results))

        # ── 4. Map to SearchResult ────────────────────────────────────────────
        search_results = [_map_result(r) for r in raw_results]

        # ── 5. Rerank (with config overrides) ────────────────────────────────
        from app.retrieval.reranker import get_reranker
        reranker = get_reranker(
            strategy=cfg.rerank_strategy,
            top_k=cfg.top_k_rerank,
            min_score=cfg.min_score,
        )
        top_results = reranker.rerank(search_results)
        _log.info("retrieval_rerank_complete", top_count=len(top_results))

        # ── 6. Build context ──────────────────────────────────────────────────
        ctx_builder = ContextBuilder(max_tokens=cfg.max_context_tokens)
        context, ctx_tokens = ctx_builder.build(top_results)

        # ── 7. Build citations ────────────────────────────────────────────────
        citations = self._cite.build(top_results)

        # ── 8. Build prompt ───────────────────────────────────────────────────
        prompt = self._prompt.build(context=context, query=query)

        return RetrievalResult(
            query=query,
            chunks_found=len(top_results),
            context=context,
            prompt=prompt,
            citations=citations,
            context_token_count=ctx_tokens,
            results=top_results,
        )

    def _empty_result(self, query: str) -> RetrievalResult:
        prompt = self._prompt.build(context="", query=query)
        return RetrievalResult(
            query=query,
            chunks_found=0,
            context="",
            prompt=prompt,
            citations=[],
            context_token_count=0,
            results=[],
        )
