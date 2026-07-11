"""Token-based sliding-window text chunker.

Splits cleaned text into overlapping chunks that respect word boundaries.
Uses tiktoken (cl100k_base) for accurate token counting when available;
falls back to a character-length approximation otherwise.

Design:
  - Always splits on whitespace boundaries (never mid-word).
  - Produces overlapping windows to preserve cross-chunk context.
  - A chunk that would exceed chunk_size is emitted early rather than
    silently truncated.

Defaults (configurable):
  chunk_size = 800 tokens
  overlap    = 100 tokens
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

# ── Tokenisation backend ──────────────────────────────────────────────────────

try:
    import tiktoken as _tiktoken

    _ENC = _tiktoken.get_encoding("cl100k_base")
    _HAS_TIKTOKEN = True
except ImportError:
    _HAS_TIKTOKEN = False
    _ENC = None  # type: ignore[assignment]


def count_tokens(text: str) -> int:
    """Return approximate token count for *text*.

    Uses tiktoken (cl100k_base encoding, same as GPT-4 and
    text-embedding-3-small) when available.  Falls back to
    ``max(1, len(text) // 4)`` — accurate to ±10 % for English prose.
    """
    if _HAS_TIKTOKEN and _ENC is not None:
        return len(_ENC.encode(text))
    return max(1, len(text) // 4)


def has_tiktoken() -> bool:
    """Return True if tiktoken is installed and the encoding loaded."""
    return _HAS_TIKTOKEN


# ── Raw chunk dataclass ───────────────────────────────────────────────────────

@dataclass
class RawChunk:
    """Intermediate chunk produced by the chunker before validation/metadata."""

    text: str
    token_count: int
    section: str = ""
    page: int | None = None
    extra_metadata: dict = field(default_factory=dict)


# ── Chunker ───────────────────────────────────────────────────────────────────

class TokenChunker:
    """Word-boundary token-window chunker with configurable overlap.

    Args:
        chunk_size: Maximum tokens per chunk. Default 800.
        overlap: Tokens shared between consecutive chunks. Default 100.
            Must be strictly less than ``chunk_size``.

    Raises:
        ValueError: If ``overlap >= chunk_size``.
    """

    def __init__(self, chunk_size: int = 800, overlap: int = 100) -> None:
        if overlap >= chunk_size:
            raise ValueError(
                f"overlap ({overlap}) must be less than chunk_size ({chunk_size})"
            )
        self.chunk_size = chunk_size
        self.overlap = overlap

    # ── Public API ────────────────────────────────────────────────────────────

    def chunk(self, text: str, section: str = "") -> list[RawChunk]:
        """Chunk *text* into overlapping token windows.

        Args:
            text: Cleaned text to split (may be a full section or a sub-block).
            section: Section heading to attach to every produced chunk.

        Returns:
            Ordered list of :class:`RawChunk` objects. Empty when *text*
            contains no non-whitespace content.
        """
        words = text.split()
        if not words:
            return []
        return self._build_chunks(words, section)

    def chunk_sections(
        self, section_blocks: Sequence[tuple[str, str]]
    ) -> list[RawChunk]:
        """Chunk multiple ``(text, section)`` pairs into a flat list.

        Args:
            section_blocks: Sequence of ``(block_text, section_title)`` pairs
                as returned by :class:`~app.chunking.section_detector.SectionDetector`.

        Returns:
            Flat ordered list of :class:`RawChunk` objects.
        """
        result: list[RawChunk] = []
        for text, section in section_blocks:
            result.extend(self.chunk(text, section=section))
        return result

    # ── Core algorithm ────────────────────────────────────────────────────────

    def _build_chunks(self, words: list[str], section: str) -> list[RawChunk]:
        chunks: list[RawChunk] = []
        start = 0

        while start < len(words):
            # ── accumulate words until chunk_size tokens ──────────────────────
            end = start
            accumulated_tokens = 0

            while end < len(words):
                word_tokens = count_tokens(words[end])
                if accumulated_tokens + word_tokens > self.chunk_size and end > start:
                    break
                accumulated_tokens += word_tokens
                end += 1

            # Guard: always advance by at least one word
            if end == start:
                end = start + 1

            chunk_text = " ".join(words[start:end])
            # Recount on the full joined string for accuracy
            token_count = count_tokens(chunk_text)

            chunks.append(
                RawChunk(text=chunk_text, token_count=token_count, section=section)
            )

            # ── slide forward, keeping ~overlap tokens ────────────────────────
            next_start = self._compute_next_start(words, start, end)
            # Safety: always advance
            start = max(next_start, start + 1)

        return chunks

    def _compute_next_start(
        self, words: list[str], chunk_start: int, chunk_end: int
    ) -> int:
        """Return the word index where the next chunk should begin.

        Walks backwards from *chunk_end* counting tokens until we have
        accumulated approximately ``self.overlap`` tokens; that word
        index becomes the start of the next chunk.
        """
        overlap_tokens = 0
        overlap_words = 0
        for i in range(chunk_end - 1, chunk_start - 1, -1):
            overlap_tokens += count_tokens(words[i])
            overlap_words += 1
            if overlap_tokens >= self.overlap:
                break
        return chunk_end - overlap_words
