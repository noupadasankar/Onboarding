"""Tests for TokenChunker and count_tokens."""
import pytest

from app.chunking.token_chunker import RawChunk, TokenChunker, count_tokens


# ── count_tokens ──────────────────────────────────────────────────────────────

class TestCountTokens:
    def test_empty_string(self) -> None:
        assert count_tokens("") >= 0

    def test_single_word(self) -> None:
        assert count_tokens("hello") >= 1

    def test_longer_text_more_tokens(self) -> None:
        short = count_tokens("Hello world")
        long = count_tokens("Hello world. " * 20)
        assert long > short

    def test_returns_int(self) -> None:
        assert isinstance(count_tokens("test"), int)


# ── TokenChunker ──────────────────────────────────────────────────────────────

@pytest.fixture
def chunker() -> TokenChunker:
    return TokenChunker(chunk_size=100, overlap=20)


class TestTokenChunkerInit:
    def test_default_params(self) -> None:
        ch = TokenChunker()
        assert ch.chunk_size == 800
        assert ch.overlap == 100

    def test_overlap_must_be_less_than_chunk_size(self) -> None:
        with pytest.raises(ValueError):
            TokenChunker(chunk_size=100, overlap=100)

    def test_overlap_greater_than_chunk_size_raises(self) -> None:
        with pytest.raises(ValueError):
            TokenChunker(chunk_size=100, overlap=200)


class TestTokenChunkerChunk:
    def test_empty_text_returns_empty(self, chunker: TokenChunker) -> None:
        assert chunker.chunk("") == []

    def test_whitespace_only_returns_empty(self, chunker: TokenChunker) -> None:
        assert chunker.chunk("   \n\n\t  ") == []

    def test_short_text_single_chunk(self, chunker: TokenChunker) -> None:
        text = "Hello world. This is a short document."
        chunks = chunker.chunk(text)
        assert len(chunks) == 1

    def test_chunk_is_rawchunk_instance(self, chunker: TokenChunker) -> None:
        chunks = chunker.chunk("Some text for testing purposes.")
        assert all(isinstance(c, RawChunk) for c in chunks)

    def test_section_attached_to_chunks(self, chunker: TokenChunker) -> None:
        chunks = chunker.chunk("Some text.", section="Leave Policy")
        assert all(c.section == "Leave Policy" for c in chunks)

    def test_token_count_populated(self, chunker: TokenChunker) -> None:
        chunks = chunker.chunk("Hello world testing.")
        assert all(c.token_count > 0 for c in chunks)

    def test_chunk_text_non_empty(self, chunker: TokenChunker) -> None:
        chunks = chunker.chunk("Non empty content here.")
        assert all(c.text.strip() for c in chunks)

    def test_large_text_multiple_chunks(self) -> None:
        # Use a small chunk_size to force multiple chunks
        ch = TokenChunker(chunk_size=20, overlap=5)
        text = " ".join([f"word{i}" for i in range(200)])
        chunks = ch.chunk(text)
        assert len(chunks) > 1

    def test_all_words_covered(self) -> None:
        """All words from the original text should appear in at least one chunk."""
        ch = TokenChunker(chunk_size=30, overlap=5)
        words = [f"word{i}" for i in range(50)]
        text = " ".join(words)
        chunks = ch.chunk(text)
        combined = " ".join(c.text for c in chunks)
        for word in words:
            assert word in combined

    def test_chunk_size_not_exceeded_significantly(self) -> None:
        """No chunk should vastly exceed chunk_size tokens."""
        ch = TokenChunker(chunk_size=50, overlap=10)
        text = " ".join(["hello"] * 200)
        chunks = ch.chunk(text)
        # Allow a small margin for the last word that might push slightly over
        for c in chunks:
            assert c.token_count <= ch.chunk_size + 10

    def test_overlap_produces_shared_content(self) -> None:
        """Consecutive chunks should share some words (due to overlap)."""
        ch = TokenChunker(chunk_size=30, overlap=10)
        text = " ".join([f"w{i}" for i in range(100)])
        chunks = ch.chunk(text)
        if len(chunks) >= 2:
            words_0 = set(chunks[0].text.split())
            words_1 = set(chunks[1].text.split())
            # There should be some overlap
            assert len(words_0 & words_1) > 0


class TestTokenChunkerChunkSections:
    def test_multiple_sections_flattened(self, chunker: TokenChunker) -> None:
        blocks = [
            ("Introduction text here.", "Introduction"),
            ("Leave policy details here.", "Leave Policy"),
        ]
        chunks = chunker.chunk_sections(blocks)
        assert len(chunks) >= 2

    def test_empty_section_block_skipped(self, chunker: TokenChunker) -> None:
        blocks = [
            ("", "Empty Section"),
            ("Real content here.", "Real Section"),
        ]
        chunks = chunker.chunk_sections(blocks)
        assert all(c.text.strip() for c in chunks)

    def test_section_titles_preserved(self, chunker: TokenChunker) -> None:
        blocks = [
            ("Content for section A.", "Section A"),
            ("Content for section B.", "Section B"),
        ]
        chunks = chunker.chunk_sections(blocks)
        titles = {c.section for c in chunks}
        assert "Section A" in titles
        assert "Section B" in titles
