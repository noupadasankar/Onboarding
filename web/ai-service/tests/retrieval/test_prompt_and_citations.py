"""Tests for PromptBuilder and CitationBuilder."""
import pytest

from app.models.search_result import SearchResult
from app.retrieval.citation_builder import CitationBuilder
from app.retrieval.prompt_builder import PromptBuilder, PromptTemplate


def _r(
    chunk_id: str = "c1",
    filename: str = "handbook.pdf",
    page: int | None = 5,
    section: str = "Leave Policy",
    score: float = 0.9,
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id="doc1",
        text="Employees receive 20 days of annual leave.",
        score=score,
        filename=filename,
        page=page,
        section=section,
    )


class TestPromptBuilder:
    def test_contains_system_prompt(self) -> None:
        prompt = PromptBuilder().build("Some context.", "How many leave days?")
        assert "OptiAgent" in prompt

    def test_contains_context(self) -> None:
        prompt = PromptBuilder().build("Context text here.", "Question?")
        assert "Context text here." in prompt

    def test_contains_query(self) -> None:
        prompt = PromptBuilder().build("ctx", "How many leave days?")
        assert "How many leave days?" in prompt

    def test_empty_context_uses_fallback(self) -> None:
        prompt = PromptBuilder().build("", "Some question?")
        assert "couldn't find" in prompt.lower() or "No relevant" in prompt

    def test_whitespace_context_uses_fallback(self) -> None:
        prompt = PromptBuilder().build("   \n  ", "Question?")
        assert "couldn't find" in prompt.lower() or "No relevant" in prompt

    def test_build_messages_returns_list(self) -> None:
        msgs = PromptBuilder().build_messages("Context.", "Question?")
        assert isinstance(msgs, list)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"

    def test_build_messages_user_contains_context(self) -> None:
        msgs = PromptBuilder().build_messages("Important context.", "Q?")
        assert "Important context." in msgs[1]["content"]

    def test_build_messages_user_contains_query(self) -> None:
        msgs = PromptBuilder().build_messages("ctx", "How many days?")
        assert "How many days?" in msgs[1]["content"]

    def test_custom_template(self) -> None:
        template = PromptTemplate(system_prompt="You are a Finance Assistant.")
        prompt = PromptBuilder(template).build("ctx", "q")
        assert "Finance Assistant" in prompt


class TestCitationBuilder:
    def test_returns_one_citation_per_unique_source(self) -> None:
        results = [
            _r("c1", "handbook.pdf", 5, "Leave Policy"),
            _r("c2", "handbook.pdf", 5, "Leave Policy"),  # duplicate
            _r("c3", "policy.pdf", 2, "Benefits"),
        ]
        citations = CitationBuilder().build(results)
        assert len(citations) == 2

    def test_citation_has_correct_document(self) -> None:
        results = [_r("c1", "handbook.pdf", 10, "Leave Policy")]
        citations = CitationBuilder().build(results)
        assert citations[0].document == "handbook.pdf"

    def test_citation_has_correct_page(self) -> None:
        results = [_r("c1", page=12)]
        citations = CitationBuilder().build(results)
        assert citations[0].page == 12

    def test_citation_has_correct_section(self) -> None:
        results = [_r("c1", section="Working Hours")]
        citations = CitationBuilder().build(results)
        assert citations[0].section == "Working Hours"

    def test_page_minus_one_becomes_none(self) -> None:
        results = [_r("c1", page=None)]
        citations = CitationBuilder().build(results)
        assert citations[0].page is None

    def test_empty_results_returns_empty(self) -> None:
        assert CitationBuilder().build([]) == []

    def test_chunk_id_in_citation(self) -> None:
        results = [_r("special_chunk")]
        citations = CitationBuilder().build(results)
        assert citations[0].chunk_id == "special_chunk"

    def test_score_in_citation(self) -> None:
        results = [_r("c1", score=0.87654)]
        citations = CitationBuilder().build(results)
        assert abs(citations[0].score - 0.8765) < 0.001
