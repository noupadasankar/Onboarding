"""Tests for reranker implementations."""
import pytest

from app.models.search_result import SearchResult
from app.retrieval.reranker import DiversityReranker, ScoreReranker, get_reranker


def _r(chunk_id: str, score: float, doc_id: str = "doc1", section: str = "") -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id=doc_id,
        text=f"text for {chunk_id}",
        score=score,
        filename="handbook.pdf",
        section=section,
    )


class TestScoreReranker:
    def test_sorts_by_score_descending(self) -> None:
        results = [_r("c1", 0.5), _r("c2", 0.9), _r("c3", 0.7)]
        top = ScoreReranker(top_k=3).rerank(results)
        assert [r.chunk_id for r in top] == ["c2", "c3", "c1"]

    def test_truncates_to_top_k(self) -> None:
        results = [_r(f"c{i}", float(i) / 10) for i in range(10)]
        top = ScoreReranker(top_k=3).rerank(results)
        assert len(top) == 3

    def test_assigns_rank_starting_at_zero(self) -> None:
        results = [_r("c1", 0.8), _r("c2", 0.6)]
        top = ScoreReranker(top_k=2).rerank(results)
        assert top[0].rank == 0
        assert top[1].rank == 1

    def test_filters_below_min_score(self) -> None:
        results = [_r("c1", 0.9), _r("c2", 0.1), _r("c3", 0.8)]
        top = ScoreReranker(top_k=5, min_score=0.5).rerank(results)
        assert len(top) == 2
        assert all(r.score >= 0.5 for r in top)

    def test_empty_input(self) -> None:
        assert ScoreReranker().rerank([]) == []

    def test_single_result(self) -> None:
        top = ScoreReranker(top_k=5).rerank([_r("c1", 0.7)])
        assert len(top) == 1
        assert top[0].rank == 0


class TestDiversityReranker:
    def test_interleaves_different_documents(self) -> None:
        results = [
            _r("c1", 0.9, "doc1"),
            _r("c2", 0.8, "doc1"),
            _r("c3", 0.7, "doc2"),
        ]
        top = DiversityReranker(top_k=3).rerank(results)
        ids = [r.chunk_id for r in top]
        assert "c1" in ids
        assert "c3" in ids

    def test_truncates_to_top_k(self) -> None:
        results = [_r(f"c{i}", 0.9 - i * 0.05, f"doc{i}") for i in range(10)]
        top = DiversityReranker(top_k=4).rerank(results)
        assert len(top) == 4

    def test_empty_input(self) -> None:
        assert DiversityReranker().rerank([]) == []


class TestGetReranker:
    def test_score_strategy(self) -> None:
        assert isinstance(get_reranker("score"), ScoreReranker)

    def test_diversity_strategy(self) -> None:
        assert isinstance(get_reranker("diversity"), DiversityReranker)

    def test_unknown_strategy_defaults_to_score(self) -> None:
        assert isinstance(get_reranker("nonexistent"), ScoreReranker)
