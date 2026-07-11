"""Tests for HybridRetriever — BM25 + dense Reciprocal Rank Fusion.

Test matrix:
  1. BM25 preferentially surfaces exact keyword matches (HR-204, TE-004, £150).
  2. RRF correctly combines dense and sparse ranked lists.
  3. Chunks surfaced by BM25 but outside the dense top-k can appear in the result.
  4. Graceful degradation: empty corpus → return dense; rank_bm25 missing → return dense.
  5. Integration with a real in-memory VectorService.

The LocalProvider produces deterministic pseudo-random embeddings — semantic
similarity is meaningless in these tests.  We rely entirely on BM25 scoring
for keyword recall verification.
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from app.models.vector_document import VectorSearchResult
from app.retrieval.hybrid_retriever import HybridRetriever
from app.repositories.vector_repository import VectorRepository
from app.services.vector_service import VectorService
from app.vectorstore.chroma_client import ChromaClient


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_result(chunk_id: str, doc_id: str = "doc1", score: float = 0.9) -> VectorSearchResult:
    return VectorSearchResult(
        chunk_id=chunk_id,
        document_id=doc_id,
        text=chunk_id,   # text = chunk_id so BM25 can distinguish them
        score=score,
        metadata={"department": "HR"},
    )


def _make_vec_svc(corpus: list[dict]) -> VectorService:
    """VectorService whose ``get_all_text`` returns *corpus* (other methods mocked)."""
    svc = MagicMock(spec=VectorService)
    svc.get_all_text.return_value = corpus
    return svc


def _corpus_entry(chunk_id: str, text: str, doc_id: str = "doc1") -> dict:
    return {
        "chunk_id": chunk_id,
        "text": text,
        "document_id": doc_id,
        "metadata": {"department": "HR"},
    }


# ── BM25 keyword recall ────────────────────────────────────────────────────────

class TestBM25KeywordRecall:
    """BM25 must score exact identifiers higher than unrelated chunks."""

    def _run_hybrid(
        self,
        query: str,
        corpus: list[dict],
        dense_results: list[VectorSearchResult],
        n: int = 10,
    ) -> list[VectorSearchResult]:
        svc = _make_vec_svc(corpus)
        retriever = HybridRetriever(vector_service=svc)
        return retriever.retrieve(
            query_text=query,
            dense_results=dense_results,
            n_results=n,
        )

    def test_exact_policy_code_hr204_surfaces_correctly(self) -> None:
        """'HR-204' query must rank the HR-204 chunk at or near the top."""
        corpus = [
            _corpus_entry("c_hr204", "Leave policy HR-204 entitles employees to annual leave."),
            _corpus_entry("c_onboard", "Onboarding process: complete compliance training."),
            _corpus_entry("c_payroll", "Payroll is processed on the last business day."),
        ]
        # Dense results put c_onboard first (simulated semantic score)
        dense = [
            _make_result("c_onboard", score=0.95),
            _make_result("c_payroll", score=0.80),
            _make_result("c_hr204",  score=0.60),  # semantic rank 3
        ]
        results = self._run_hybrid("HR-204", corpus, dense)
        ids = [r.chunk_id for r in results]
        # HR-204 chunk must be in the results
        assert "c_hr204" in ids
        # HR-204 should rank higher than it did in dense-only (was rank 3)
        assert ids.index("c_hr204") < ids.index("c_onboard") or ids.index("c_hr204") <= 1

    def test_exact_policy_code_te004_surfaces_correctly(self) -> None:
        """'TE-004' query surfaces the TE-004 chunk even if dense ranks it last."""
        corpus = [
            _corpus_entry("c_te004",  "Mental health leave policy TE-004: 3 days per year."),
            _corpus_entry("c_annual", "Employees receive 20 days annual leave per year."),
            _corpus_entry("c_salary", "Salary reviews are conducted in Q1 each year."),
        ]
        dense = [
            _make_result("c_salary", score=0.92),
            _make_result("c_annual", score=0.85),
            _make_result("c_te004",  score=0.50),
        ]
        results = self._run_hybrid("TE-004", corpus, dense)
        ids = [r.chunk_id for r in results]
        assert "c_te004" in ids
        # TE-004 chunk should move up relative to its dense rank
        assert ids.index("c_te004") < 2

    def test_currency_amount_gbp_150_found(self) -> None:
        """Exact monetary value '£150' must be recalled by BM25."""
        corpus = [
            _corpus_entry("c_travel", "Travel allowance is £150 per month for commuters."),
            _corpus_entry("c_leave",  "Leave policy: 20 days annual leave per year."),
            _corpus_entry("c_bonus",  "Performance bonuses are paid in December annually."),
        ]
        dense = [
            _make_result("c_leave",  score=0.90),
            _make_result("c_bonus",  score=0.80),
            _make_result("c_travel", score=0.55),
        ]
        results = self._run_hybrid("£150", corpus, dense)
        ids = [r.chunk_id for r in results]
        assert "c_travel" in ids
        # BM25 should promote c_travel significantly
        assert ids.index("c_travel") <= 1

    def test_section_number_surfaces_relevant_chunk(self) -> None:
        """Query '7.2' should surface the chunk that literally contains '7.2'."""
        corpus = [
            _corpus_entry("c_72",     "Section 7.2 covers hybrid working arrangements."),
            _corpus_entry("c_intro",  "This handbook covers all HR policies."),
            _corpus_entry("c_health", "Mental health support is available to all staff."),
        ]
        dense = [
            _make_result("c_health", score=0.88),
            _make_result("c_intro",  score=0.75),
            _make_result("c_72",     score=0.52),
        ]
        results = self._run_hybrid("7.2", corpus, dense)
        ids = [r.chunk_id for r in results]
        assert "c_72" in ids

    def test_semantic_query_still_includes_dense_top(self) -> None:
        """Broad semantic queries don't demote the dense top result drastically."""
        corpus = [
            _corpus_entry("c_leave",  "Employees receive 20 days annual leave per year."),
            _corpus_entry("c_policy", "HR policy is reviewed annually by the board."),
        ]
        dense = [_make_result("c_leave", score=0.95), _make_result("c_policy", score=0.70)]
        results = self._run_hybrid("how many days off do staff get", corpus, dense)
        # Dense top result should appear in fused results
        assert results[0].chunk_id == "c_leave"

    def test_annual_leave_phrase_broad_recall(self) -> None:
        """Multi-word query 'Annual Leave' finds all relevant chunks."""
        corpus = [
            _corpus_entry("c_annual", "Annual leave: 20 days per year."),
            _corpus_entry("c_carry",  "Unused annual leave may be carried over."),
            _corpus_entry("c_sick",   "Sick leave is separate from annual leave."),
            _corpus_entry("c_payroll","Payroll processed monthly."),
        ]
        dense = [
            _make_result("c_annual", score=0.90),
            _make_result("c_carry",  score=0.85),
            _make_result("c_sick",   score=0.80),
            _make_result("c_payroll",score=0.60),
        ]
        results = self._run_hybrid("Annual Leave", corpus, dense)
        ids = {r.chunk_id for r in results}
        # All three leave-related chunks should appear
        assert {"c_annual", "c_carry", "c_sick"}.issubset(ids)


# ── RRF fusion mechanics ──────────────────────────────────────────────────────

class TestRRFFusion:
    """Reciprocal Rank Fusion formula and result ordering tests."""

    def _hybrid(
        self,
        query: str,
        corpus: list[dict],
        dense: list[VectorSearchResult],
        n: int = 10,
    ) -> list[VectorSearchResult]:
        svc = _make_vec_svc(corpus)
        return HybridRetriever(vector_service=svc).retrieve(
            query_text=query, dense_results=dense, n_results=n,
        )

    def test_scores_are_positive(self) -> None:
        """All RRF scores must be strictly positive."""
        corpus = [
            _corpus_entry("c_a", "Annual leave policy document HR-204."),
            _corpus_entry("c_b", "Salary grades and compensation table."),
        ]
        dense = [_make_result("c_a", score=0.9), _make_result("c_b", score=0.7)]
        results = self._hybrid("HR-204", corpus, dense)
        for r in results:
            assert r.score > 0.0

    def test_result_count_bounded_by_n_results(self) -> None:
        """Fused list must never exceed *n_results*."""
        corpus = [_corpus_entry(f"c_{i}", f"chunk text {i}") for i in range(20)]
        dense = [_make_result(f"c_{i}", score=1.0 - i * 0.04) for i in range(20)]
        results = self._hybrid("chunk text", corpus, dense, n=5)
        assert len(results) <= 5

    def test_dense_and_bm25_agreement_puts_chunk_first(self) -> None:
        """When dense and BM25 both rank a chunk first, it wins RRF."""
        corpus = [
            _corpus_entry("c_winner", "HR-204 leave policy winner document."),
            _corpus_entry("c_other",  "Unrelated payroll information."),
        ]
        dense = [
            _make_result("c_winner", score=0.99),
            _make_result("c_other",  score=0.50),
        ]
        results = self._hybrid("HR-204", corpus, dense)
        assert results[0].chunk_id == "c_winner"

    def test_bm25_only_chunk_surfaces_when_not_in_dense(self) -> None:
        """A chunk with a strong BM25 match but absent from dense results must appear."""
        # c_bm25_only is in the corpus but NOT in dense_results
        corpus = [
            _corpus_entry("c_bm25_only", "Policy code BUPA-001 medical insurance scheme."),
            _corpus_entry("c_dense1",    "Leave entitlement for permanent staff."),
            _corpus_entry("c_dense2",    "Payroll processing schedule quarterly."),
        ]
        dense = [
            _make_result("c_dense1", score=0.88),
            _make_result("c_dense2", score=0.75),
            # c_bm25_only intentionally absent from dense results
        ]
        results = self._hybrid("BUPA-001", corpus, dense)
        ids = [r.chunk_id for r in results]
        assert "c_bm25_only" in ids

    def test_rrf_scores_decrease_monotonically(self) -> None:
        """Results should be sorted in descending RRF score order."""
        corpus = [
            _corpus_entry("c_a", "HR-204 leave policy primary document."),
            _corpus_entry("c_b", "Secondary HR policy overview."),
            _corpus_entry("c_c", "Finance payroll processing guide."),
        ]
        dense = [
            _make_result("c_a", score=0.95),
            _make_result("c_b", score=0.80),
            _make_result("c_c", score=0.65),
        ]
        results = self._hybrid("HR-204", corpus, dense)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_empty_dense_with_bm25_match(self) -> None:
        """Even with empty dense results, BM25 can populate the list."""
        corpus = [
            _corpus_entry("c_kw", "Policy HR-204 keyword match chunk."),
        ]
        results = self._hybrid("HR-204", corpus, dense_results=[], n=5)
        # BM25 should surface c_kw even without any dense results
        ids = [r.chunk_id for r in results]
        assert "c_kw" in ids


# ── Graceful degradation ──────────────────────────────────────────────────────

class TestGracefulDegradation:
    """HybridRetriever must never crash; it falls back to dense when necessary."""

    def test_empty_corpus_returns_dense_results_unchanged(self) -> None:
        """When get_all_text returns [], fall back to dense unchanged."""
        svc = _make_vec_svc([])
        dense = [_make_result("c_a"), _make_result("c_b")]
        results = HybridRetriever(vector_service=svc).retrieve(
            query_text="leave policy", dense_results=dense, n_results=10,
        )
        ids = [r.chunk_id for r in results]
        assert "c_a" in ids
        assert "c_b" in ids

    def test_empty_corpus_dense_order_preserved(self) -> None:
        """With empty corpus, dense order must be preserved exactly."""
        svc = _make_vec_svc([])
        dense = [
            _make_result("first",  score=0.9),
            _make_result("second", score=0.7),
            _make_result("third",  score=0.5),
        ]
        results = HybridRetriever(vector_service=svc).retrieve(
            query_text="query", dense_results=dense,
        )
        assert [r.chunk_id for r in results] == ["first", "second", "third"]

    def test_query_with_no_bm25_tokens_returns_dense(self) -> None:
        """A query that produces zero BM25 scores for all chunks still returns results."""
        corpus = [
            _corpus_entry("c_a", "Annual leave entitlement."),
            _corpus_entry("c_b", "Payroll processing guide."),
        ]
        svc = _make_vec_svc(corpus)
        dense = [_make_result("c_a"), _make_result("c_b")]
        # Query that won't match any corpus tokens
        results = HybridRetriever(vector_service=svc).retrieve(
            query_text="xyzzy-nonexistent-token-12345",
            dense_results=dense,
        )
        # Dense should still be present
        assert len(results) >= 1

    def test_rank_bm25_missing_falls_back_gracefully(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When rank_bm25 is not importable, return dense results unchanged."""
        import builtins
        real_import = builtins.__import__

        def _no_rank_bm25(name, *args, **kwargs):
            if name == "rank_bm25":
                raise ImportError("No module named 'rank_bm25'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _no_rank_bm25)

        corpus = [_corpus_entry("c_a", "Leave policy HR-204.")]
        svc = _make_vec_svc(corpus)
        dense = [_make_result("c_a", score=0.95)]

        results = HybridRetriever(vector_service=svc).retrieve(
            query_text="HR-204",
            dense_results=dense,
        )
        assert any(r.chunk_id == "c_a" for r in results)

    def test_n_results_respected_with_large_corpus(self) -> None:
        """n_results cap is always respected even with very large corpus."""
        corpus = [_corpus_entry(f"c_{i}", f"chunk {i} annual leave HR-204") for i in range(100)]
        svc = _make_vec_svc(corpus)
        dense = [_make_result(f"c_{i}", score=1.0 - i * 0.009) for i in range(30)]
        results = HybridRetriever(vector_service=svc).retrieve(
            query_text="HR-204", dense_results=dense, n_results=5,
        )
        assert len(results) <= 5


# ── Integration: real VectorService (in-memory Chroma) ────────────────────────

class TestHybridRetrieverIntegration:
    """Integration tests using a real VectorService backed by in-memory ChromaDB.

    These tests pre-populate the collection, then verify HybridRetriever
    can surface keyword matches that might not appear in the dense top-k.
    """

    @pytest.fixture(scope="class")
    def loaded_service(self) -> VectorService:
        """VectorService pre-loaded with known HR policy chunks."""
        from app.embeddings.embedding_pipeline import EmbeddingPipeline
        from app.embeddings.providers.local_provider import LocalProvider
        from app.models.chunk import Chunk

        _DIMS = 64
        provider = LocalProvider(dimensions=_DIMS)
        pipeline = EmbeddingPipeline(provider=provider)

        client = ChromaClient(mode="memory")
        repo = VectorRepository(client=client, collection_name="test_hybrid_integration")
        svc = VectorService(repo)

        chunks_data = [
            ("hr204_leave",     "HR-204 annual leave policy: employees receive 20 days."),
            ("te004_mental",    "Policy TE-004 mental health leave: 3 days per year."),
            ("bupa_medical",    "BUPA medical insurance: £150 monthly employer contribution."),
            ("section72",       "Section 7.2 hybrid working: up to 3 days per week from home."),
            ("payroll_general", "Payroll is processed on the last working day of each month."),
            ("onboarding",      "New starter onboarding: complete mandatory training in week 1."),
            ("salary_review",   "Annual salary review takes place in Q1 of each year."),
        ]

        chunks = [
            Chunk(
                chunk_id=cid,
                document_id="integration_doc",
                chunk_index=i,
                text=text,
                token_count=len(text.split()),
                metadata={"filename": "handbook.pdf", "department": "HR"},
            )
            for i, (cid, text) in enumerate(chunks_data)
        ]

        embedded = asyncio.get_event_loop().run_until_complete(
            pipeline.run(chunks, document_filename="handbook.pdf")
        )
        chunk_texts = {c.chunk_id: c.text for c in chunks}
        svc.index(embedded, chunk_texts)
        return svc

    def test_get_all_text_returns_corpus(self, loaded_service: VectorService) -> None:
        """get_all_text() must return the pre-loaded corpus (used by HybridRetriever)."""
        corpus = loaded_service.get_all_text()
        assert len(corpus) == 7
        chunk_ids = {entry["chunk_id"] for entry in corpus}
        assert "hr204_leave" in chunk_ids
        assert "te004_mental" in chunk_ids

    def test_hr204_found_in_fused_results(self, loaded_service: VectorService) -> None:
        """HR-204 identifier must appear in hybrid results for 'HR-204' query."""
        # Simulate dense results that rank HR-204 low (as pure semantic often does)
        corpus = loaded_service.get_all_text()
        dense = [
            _make_result("payroll_general",  score=0.80),
            _make_result("onboarding",        score=0.75),
            _make_result("salary_review",     score=0.70),
            _make_result("section72",         score=0.65),
            _make_result("hr204_leave",       score=0.50),  # rank 5 in dense
        ]
        hybrid = HybridRetriever(vector_service=loaded_service)
        results = hybrid.retrieve(
            query_text="HR-204",
            dense_results=dense,
            n_results=5,
        )
        ids = [r.chunk_id for r in results]
        assert "hr204_leave" in ids
        # HR-204 chunk should move from rank 5 to top 2
        assert ids.index("hr204_leave") <= 1

    def test_bupa_insurance_found_by_keyword(self, loaded_service: VectorService) -> None:
        """'BUPA' identifier not in dense top-k should be surfaced by BM25."""
        dense = [
            _make_result("hr204_leave",   score=0.90),
            _make_result("te004_mental",  score=0.85),
            _make_result("payroll_general", score=0.80),
            # bupa_medical absent from dense
        ]
        hybrid = HybridRetriever(vector_service=loaded_service)
        results = hybrid.retrieve(
            query_text="BUPA",
            dense_results=dense,
            n_results=5,
        )
        ids = [r.chunk_id for r in results]
        assert "bupa_medical" in ids

    def test_department_scoped_get_all_text(self, loaded_service: VectorService) -> None:
        """department kwarg is passed through to VectorService.get_all_text()."""
        # All integration chunks have department=HR, so HR scope returns them all
        corpus = loaded_service.get_all_text(department="HR")
        assert len(corpus) == 7

        # Finance scope returns nothing (no Finance chunks were indexed)
        finance_corpus = loaded_service.get_all_text(department="Finance")
        assert len(finance_corpus) == 0
