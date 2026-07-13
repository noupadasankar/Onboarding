"""Hybrid retriever — fuses dense (semantic) and sparse (BM25) search via RRF.

Algorithm
---------
1.  Fetch full corpus for the scoped department from ChromaDB (text only —
    no embeddings, so this is fast).
2.  Build a BM25Okapi index from the corpus.
3.  Score the query against that index; build a BM25 ranked list.
4.  Receive the dense ranked list from the caller (already computed by
    VectorService.search).
5.  Apply Reciprocal Rank Fusion (RRF) across both lists.
6.  Return the fused list as VectorSearchResult objects, ordered by combined
    RRF score (descending), limited to *n_results*.

Graceful degradation
--------------------
If ``rank_bm25`` is not installed the module logs a warning and returns the
dense results unchanged — no crash, no API breakage.

RRF formula
-----------
    score[chunk_id] += 1 / (k + rank + 1)

where *k* is the smoothing constant (default 60, standard in the literature).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.models.vector_document import VectorSearchResult
    from app.services.vector_service import VectorService

_log = get_logger()

_RRF_K: int = 60  # standard smoothing constant for Reciprocal Rank Fusion


def _rrf_score(rank: int, k: int = _RRF_K) -> float:
    """Return the RRF contribution for a result at position *rank* (0-indexed)."""
    return 1.0 / (k + rank + 1)


class HybridRetriever:
    """BM25 + dense semantic search fused with Reciprocal Rank Fusion.

    Args:
        vector_service: Used to fetch the department-scoped corpus for BM25.
    """

    def __init__(self, vector_service: "VectorService") -> None:
        self._vs = vector_service

    def retrieve(
        self,
        query_text: str,
        dense_results: "list[VectorSearchResult]",
        department: "str | None" = None,
        departments: "list[str] | None" = None,
        n_results: int = 20,
    ) -> "list[VectorSearchResult]":
        """Return a RRF-fused result list.

        Args:
            query_text: Raw (normalised) user query for BM25 scoring.
            dense_results: Pre-computed dense search results (VectorSearchResult
                list, highest similarity first).
            department: Optional single-department scope for the BM25 corpus.
            departments: Optional department whitelist for the BM25 corpus.
                Takes precedence over *department*.
            n_results: Maximum number of results to return.

        Returns:
            Fused list of VectorSearchResult, ordered by combined RRF score
            (descending).  Falls back to *dense_results* unchanged if
            ``rank_bm25`` is unavailable or the corpus is empty.
        """
        try:
            from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]
        except ImportError:
            _log.warning(
                "rank_bm25 not installed — falling back to dense-only search. "
                "Install with: pip install rank-bm25"
            )
            return dense_results[:n_results]

        # ── 1. Fetch corpus (same scoping as dense search: dept + is_latest) ──
        corpus = self._vs.get_all_text(department=department, departments=departments)
        if not corpus:
            _log.debug("hybrid_retriever: empty corpus, returning dense results")
            return dense_results[:n_results]

        # ── 2. Build BM25 index ────────────────────────────────────────────────
        # Tokenise by whitespace (fast, good enough for enterprise documents).
        tokenised = [entry["text"].lower().split() for entry in corpus]
        bm25 = BM25Okapi(tokenised)

        # ── 3. BM25 scores → ranked list ──────────────────────────────────────
        query_tokens = query_text.lower().split()
        bm25_scores: list[float] = bm25.get_scores(query_tokens).tolist()

        # Pair each corpus entry with its BM25 score, sort descending.
        bm25_ranked: list[tuple[str, float]] = sorted(
            ((entry["chunk_id"], score) for entry, score in zip(corpus, bm25_scores)),
            key=lambda x: x[1],
            reverse=True,
        )

        # ── 4. Build chunk_id → VectorSearchResult lookup ─────────────────────
        dense_map: dict[str, "VectorSearchResult"] = {
            r.chunk_id: r for r in dense_results
        }

        # Also build a lookup from corpus for chunks NOT in dense results (BM25
        # may surface chunks that fell outside the dense top-k window).
        corpus_map: dict[str, dict] = {entry["chunk_id"]: entry for entry in corpus}

        # ── 5. Reciprocal Rank Fusion ─────────────────────────────────────────
        rrf_scores: dict[str, float] = {}

        # Dense contributions
        for rank, result in enumerate(dense_results):
            cid = result.chunk_id
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + _rrf_score(rank)

        # BM25 contributions (only for chunks with a non-zero BM25 score)
        for rank, (cid, bm25_score) in enumerate(bm25_ranked):
            if bm25_score <= 0.0:
                break  # sorted descending — once we hit 0 the rest are 0 too
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + _rrf_score(rank)

        # ── 6. Build fused result list ─────────────────────────────────────────
        # Sort chunk_ids by combined RRF score, highest first.
        fused_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)

        from app.models.vector_document import VectorSearchResult

        fused: list[VectorSearchResult] = []
        for cid in fused_ids[:n_results]:
            if cid in dense_map:
                # Reuse the existing VectorSearchResult, overwrite score with RRF value
                dr = dense_map[cid]
                fused.append(
                    VectorSearchResult(
                        chunk_id=dr.chunk_id,
                        document_id=dr.document_id,
                        text=dr.text,
                        score=rrf_scores[cid],
                        metadata=dr.metadata,
                    )
                )
            elif cid in corpus_map:
                # BM25 surfaced a chunk outside the dense top-k — reconstruct it.
                entry = corpus_map[cid]
                meta = entry.get("metadata") or {}
                fused.append(
                    VectorSearchResult(
                        chunk_id=cid,
                        document_id=entry["document_id"],
                        text=entry["text"],
                        score=rrf_scores[cid],
                        metadata=meta,
                    )
                )

        _log.info(
            "hybrid_retriever_fused",
            dense_count=len(dense_results),
            bm25_corpus_size=len(corpus),
            fused_count=len(fused),
        )
        return fused
