"""Tests for ContextBuilder."""
import pytest

from app.models.search_result import SearchResult
from app.retrieval.context_builder import ContextBuilder


def _r(
    chunk_id: str,
    text: str,
    score: float = 0.9,
    token_count: int = 50,
    section: str = "",
    filename: str = "handbook.pdf",
    page: int | None = None,
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id="doc1",
        text=text,
        score=score,
        token_count=token_count,
        section=section,
        filename=filename,
        page=page,
        rank=0,
    )


class TestContextBuilder:
    def test_empty_results_returns_empty_string(self) -> None:
        ctx, tokens = ContextBuilder().build([])
        assert ctx == ""
        assert tokens == 0

    def test_single_result_includes_text(self) -> None:
        r = _r("c1", "Employees receive 20 days of annual leave.")
        ctx, _ = ContextBuilder().build([r])
        assert "Employees receive 20 days" in ctx

    def test_metadata_header_included(self) -> None:
        r = _r("c1", "Some HR text.", section="Leave Policy", page=5)
        ctx, _ = ContextBuilder(include_metadata=True).build([r])
        assert "Leave Policy" in ctx
        assert "p.5" in ctx

    def test_metadata_header_excluded(self) -> None:
        r = _r("c1", "Pure text only.", section="Leave Policy", filename="handbook.pdf")
        ctx, _ = ContextBuilder(include_metadata=False).build([r])
        assert "[" not in ctx
        assert "Pure text only." in ctx

    def test_multiple_results_separated(self) -> None:
        r1 = _r("c1", "Text one.")
        r2 = _r("c2", "Text two.")
        ctx, _ = ContextBuilder().build([r1, r2])
        assert "Text one." in ctx
        assert "Text two." in ctx

    def test_duplicate_chunks_skipped(self) -> None:
        r = _r("same_id", "Duplicate text.")
        ctx, _ = ContextBuilder().build([r, r])
        assert ctx.count("Duplicate text.") == 1

    def test_token_budget_respected(self) -> None:
        # Create chunks that are large enough to hit the budget
        big_text = "word " * 500   # ~500 tokens
        r1 = _r("c1", big_text, token_count=500)
        r2 = _r("c2", big_text, token_count=500)
        # Budget of 600 — only first chunk should fit
        ctx, tokens = ContextBuilder(max_tokens=600).build([r1, r2])
        assert tokens <= 700  # small margin for metadata overhead
        assert "c2" not in ctx or ctx.count(big_text[:20]) == 1

    def test_token_count_positive(self) -> None:
        r = _r("c1", "The quick brown fox jumps over the lazy dog." * 5)
        _, tokens = ContextBuilder().build([r])
        assert tokens > 0
