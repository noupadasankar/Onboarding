"""Tests for ChunkValidator."""
import pytest

from app.chunking.token_chunker import RawChunk
from app.chunking.validator import ChunkValidator


def _make(text: str, token_count: int = 100) -> RawChunk:
    """Build a RawChunk with an explicit token_count (bypasses re-counting)."""
    return RawChunk(text=text, token_count=token_count)


@pytest.fixture
def validator() -> ChunkValidator:
    return ChunkValidator(min_tokens=50)


class TestEmptyAndWhitespaceRejection:
    def test_empty_text_rejected(self, validator: ChunkValidator) -> None:
        chunk = _make("", token_count=0)
        assert not validator.is_valid(chunk)
        assert validator.rejection_reason(chunk) == "empty"

    def test_whitespace_only_rejected(self, validator: ChunkValidator) -> None:
        chunk = _make("   \n\t  ", token_count=0)
        assert not validator.is_valid(chunk)
        reason = validator.rejection_reason(chunk)
        assert reason is not None and "whitespace" in reason

    def test_empty_rejected_in_validate_all(self, validator: ChunkValidator) -> None:
        chunks = [_make(""), _make("Hello world " * 30)]
        valid = validator.validate_all(chunks)
        assert len(valid) == 1


class TestMinTokensRejection:
    def test_below_min_tokens_rejected(self) -> None:
        v = ChunkValidator(min_tokens=50)
        chunk = _make("short text", token_count=10)
        assert not v.is_valid(chunk)
        reason = v.rejection_reason(chunk)
        assert reason is not None and "too_short" in reason

    def test_exactly_min_tokens_accepted(self) -> None:
        v = ChunkValidator(min_tokens=50)
        chunk = _make("acceptable text " * 20, token_count=50)
        assert v.is_valid(chunk)

    def test_above_min_tokens_accepted(self) -> None:
        v = ChunkValidator(min_tokens=50)
        chunk = _make("long text " * 50, token_count=200)
        assert v.is_valid(chunk)

    def test_custom_min_tokens(self) -> None:
        v = ChunkValidator(min_tokens=10)
        chunk = _make("short but enough", token_count=12)
        assert v.is_valid(chunk)

    def test_zero_min_tokens_always_passes_length(self) -> None:
        v = ChunkValidator(min_tokens=0)
        chunk = _make("x", token_count=1)
        # Only non-empty check matters
        assert v.is_valid(chunk)


class TestDuplicateRejection:
    def test_duplicate_chunk_removed(self, validator: ChunkValidator) -> None:
        text = "This is a valid chunk with enough content to pass validation. " * 5
        chunks = [_make(text, 100), _make(text, 100)]
        valid = validator.validate_all(chunks)
        assert len(valid) == 1

    def test_case_insensitive_duplicate_removed(self, validator: ChunkValidator) -> None:
        base = "Duplicate content should be caught regardless of casing. " * 5
        chunks = [_make(base, 100), _make(base.upper(), 100)]
        valid = validator.validate_all(chunks)
        assert len(valid) == 1

    def test_distinct_texts_both_kept(self, validator: ChunkValidator) -> None:
        a = "Section A content. " * 10
        b = "Section B content. " * 10
        chunks = [_make(a, 100), _make(b, 100)]
        valid = validator.validate_all(chunks)
        assert len(valid) == 2

    def test_first_occurrence_kept(self, validator: ChunkValidator) -> None:
        text = "Repeated text. " * 10
        chunk_a = _make(text, 100)
        chunk_b = _make(text, 100)
        valid = validator.validate_all([chunk_a, chunk_b])
        assert valid[0] is chunk_a

    def test_dedup_disabled_keeps_both(self) -> None:
        v = ChunkValidator(min_tokens=50, remove_duplicates=False)
        text = "Same text repeated here. " * 5
        chunks = [_make(text, 100), _make(text, 100)]
        valid = v.validate_all(chunks)
        assert len(valid) == 2


class TestGibberishRejection:
    def test_high_non_printable_ratio_rejected(self, validator: ChunkValidator) -> None:
        # Insert 20% non-printable chars → above 15% threshold
        garbage = "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0b\x0c\x0e\x0f\x10"
        printable = "normal text here abc def"
        # 15 garbage chars : 24 printable chars → ~38% garbage
        text = garbage + printable
        chunk = _make(text, token_count=100)
        assert not validator.is_valid(chunk)

    def test_symbol_only_run_rejected(self, validator: ChunkValidator) -> None:
        # 60 consecutive non-alphabetic chars
        text = "!@#$%^&*()_+-=[]{}|;':\",./<>?" * 3  # 90 chars
        chunk = _make(text, token_count=100)
        assert not validator.is_valid(chunk)

    def test_normal_text_not_rejected(self, validator: ChunkValidator) -> None:
        text = "Employees are entitled to 20 days of paid annual leave per year. " * 5
        chunk = _make(text, token_count=100)
        assert validator.rejection_reason(chunk) is None

    def test_punctuation_rich_but_valid(self, validator: ChunkValidator) -> None:
        text = "Benefits: health insurance, dental, vision. Perks: gym, meals. " * 4
        chunk = _make(text, token_count=100)
        assert validator.is_valid(chunk)


class TestValidateAll:
    def test_all_valid_all_returned(self, validator: ChunkValidator) -> None:
        chunks = [_make(f"Distinct content block {i}. " * 5, 100) for i in range(5)]
        valid = validator.validate_all(chunks)
        assert len(valid) == 5

    def test_mixed_bag(self, validator: ChunkValidator) -> None:
        good = _make("Good chunk with plenty of content. " * 5, 100)
        empty = _make("", 0)
        short = _make("Too short.", 5)
        chunks = [good, empty, short]
        valid = validator.validate_all(chunks)
        assert len(valid) == 1
        assert valid[0] is good

    def test_order_preserved(self, validator: ChunkValidator) -> None:
        chunks = [_make(f"Content block {i}. " * 5, 100) for i in range(3)]
        valid = validator.validate_all(chunks)
        assert [c.text for c in valid] == [c.text for c in chunks]

    def test_empty_input_list_returns_empty(self, validator: ChunkValidator) -> None:
        assert validator.validate_all([]) == []
