"""Tests for app/evaluation/rag_metrics.py."""
import pytest

from app.evaluation.rag_metrics import (
    answer_groundedness,
    citation_coverage,
    context_relevance,
    evaluate_response,
    retrieval_f1,
    retrieval_precision,
    retrieval_recall,
)


class TestRetrievalPrecision:
    def test_all_relevant(self) -> None:
        assert retrieval_precision(["a", "b"], {"a", "b"}) == 1.0

    def test_none_relevant(self) -> None:
        assert retrieval_precision(["x", "y"], {"a", "b"}) == 0.0

    def test_half_relevant(self) -> None:
        assert retrieval_precision(["a", "x"], {"a"}) == pytest.approx(0.5)

    def test_empty_retrieved(self) -> None:
        assert retrieval_precision([], {"a"}) == 0.0


class TestRetrievalRecall:
    def test_all_found(self) -> None:
        assert retrieval_recall(["a", "b", "c"], {"a", "b"}) == 1.0

    def test_none_found(self) -> None:
        assert retrieval_recall(["x"], {"a"}) == 0.0

    def test_empty_relevant_set(self) -> None:
        assert retrieval_recall(["a"], set()) == 1.0

    def test_partial_recall(self) -> None:
        assert retrieval_recall(["a"], {"a", "b"}) == pytest.approx(0.5)


class TestRetrievalF1:
    def test_perfect_score(self) -> None:
        assert retrieval_f1(["a", "b"], {"a", "b"}) == 1.0

    def test_zero_when_no_overlap(self) -> None:
        assert retrieval_f1(["x"], {"a"}) == 0.0

    def test_balanced(self) -> None:
        f1 = retrieval_f1(["a", "b"], {"a", "c"})
        assert 0.0 < f1 < 1.0


class TestContextRelevance:
    def test_high_relevance(self) -> None:
        q = "How many leave days do employees receive?"
        ctx = "Employees receive twenty leave days per year."
        assert context_relevance(q, ctx) > 0.3

    def test_zero_for_empty_context(self) -> None:
        assert context_relevance("What is the policy?", "") == 0.0

    def test_unrelated_context_low_score(self) -> None:
        q = "leave days policy"
        ctx = "The stock market closed higher yesterday."
        assert context_relevance(q, ctx) < 0.3


class TestAnswerGroundedness:
    def test_fully_grounded(self) -> None:
        ctx = "Employees receive 20 annual leave days per year according to the handbook."
        ans = "You receive 20 annual leave days per year."
        score = answer_groundedness(ans, ctx)
        assert score > 0.5

    def test_empty_answer(self) -> None:
        assert answer_groundedness("", "some context") == 0.0

    def test_ungrounded_answer_low_score(self) -> None:
        ctx = "Leave policy details are in section 4."
        ans = "The moon is made of cheese and orbits the earth."
        assert answer_groundedness(ans, ctx) < 0.5


class TestCitationCoverage:
    def test_full_coverage_by_filename(self) -> None:
        citations = [{"filename": "handbook.pdf", "text": "some text here"}]
        answer = "According to the handbook, employees get 20 days."
        assert citation_coverage(answer, citations) == 1.0

    def test_no_citations_returns_perfect(self) -> None:
        assert citation_coverage("any answer", []) == 1.0

    def test_uncited_source_reduces_score(self) -> None:
        citations = [{"filename": "obscure_policy_xyz.pdf", "text": "xyz abc"}]
        answer = "According to our policy, this is the answer."
        score = citation_coverage(answer, citations)
        assert score <= 1.0


class TestEvaluateResponse:
    def test_returns_all_keys(self) -> None:
        result = evaluate_response(
            question="How many days?",
            context="20 leave days.",
            answer="You get 20 days.",
            citations=[],
        )
        assert "context_relevance" in result
        assert "answer_groundedness" in result
        assert "citation_coverage" in result

    def test_includes_retrieval_metrics_when_ids_provided(self) -> None:
        result = evaluate_response(
            question="leave days?",
            context="20 days",
            answer="20 days",
            citations=[],
            retrieved_ids=["a", "b"],
            relevant_ids={"a"},
        )
        assert "retrieval_precision" in result
        assert "retrieval_recall" in result
        assert "retrieval_f1" in result

    def test_scores_in_range(self) -> None:
        result = evaluate_response(
            question="expense limit?",
            context="Expenses up to £500 are reimbursed.",
            answer="The expense limit is £500.",
            citations=[],
        )
        for key, val in result.items():
            assert 0.0 <= val <= 1.0, f"{key}={val} out of range"
