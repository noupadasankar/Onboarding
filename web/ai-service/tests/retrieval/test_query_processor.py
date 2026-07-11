"""Tests for QueryProcessor."""
import pytest

from app.retrieval.query_processor import QueryProcessor, QueryProcessingError


@pytest.fixture
def processor() -> QueryProcessor:
    return QueryProcessor()


class TestNormalisation:
    def test_strips_leading_trailing_whitespace(self, processor: QueryProcessor) -> None:
        assert processor.process("  hello world  ") == "hello world"

    def test_collapses_internal_spaces(self, processor: QueryProcessor) -> None:
        assert processor.process("how  many   leave   days") == "how many leave days"

    def test_collapses_tabs(self, processor: QueryProcessor) -> None:
        result = processor.process("question\there")
        assert "\t" not in result

    def test_collapses_newlines(self, processor: QueryProcessor) -> None:
        result = processor.process("line one\nline two")
        assert "\n" not in result

    def test_deduplicates_question_marks(self, processor: QueryProcessor) -> None:
        assert processor.process("How many days???") == "How many days?"

    def test_deduplicates_exclamations(self, processor: QueryProcessor) -> None:
        assert processor.process("Tell me!!!") == "Tell me!"

    def test_preserves_ellipsis(self, processor: QueryProcessor) -> None:
        # ... is deliberate punctuation — should not be collapsed
        result = processor.process("Think about it...")
        assert "..." in result

    def test_unicode_nfkc_normalisation(self, processor: QueryProcessor) -> None:
        # Full-width A → standard A
        result = processor.process("Ａ")  # Ａ
        assert result == "A"

    def test_normal_sentence_unchanged(self, processor: QueryProcessor) -> None:
        q = "How many annual leave days do employees receive?"
        assert processor.process(q) == q


class TestLengthGuards:
    def test_empty_string_raises(self, processor: QueryProcessor) -> None:
        with pytest.raises(QueryProcessingError, match="too short"):
            processor.process("")

    def test_whitespace_only_raises(self, processor: QueryProcessor) -> None:
        with pytest.raises(QueryProcessingError, match="too short"):
            processor.process("   ")

    def test_single_char_raises(self, processor: QueryProcessor) -> None:
        with pytest.raises(QueryProcessingError):
            processor.process("?")

    def test_two_chars_accepted(self, processor: QueryProcessor) -> None:
        result = processor.process("hi")
        assert result == "hi"

    def test_over_max_length_raises(self) -> None:
        p = QueryProcessor(max_length=10)
        with pytest.raises(QueryProcessingError, match="too long"):
            p.process("a" * 11)

    def test_non_string_raises(self, processor: QueryProcessor) -> None:
        with pytest.raises(QueryProcessingError):
            processor.process(123)  # type: ignore[arg-type]
