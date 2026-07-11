"""Chunk validator — filters out low-quality chunks before embedding.

Validation rules (applied in order):
  1. Empty text → reject
  2. Whitespace-only text → reject
  3. Token count below minimum (default 50) → reject
  4. Duplicate text (exact match after normalisation) → reject
  5. Text looks like OCR gibberish → reject

Any chunk that passes all rules is considered valid.
"""
from __future__ import annotations

import re
import unicodedata

from app.chunking.token_chunker import RawChunk, count_tokens

# Minimum token count below which a chunk is considered too short to be useful
DEFAULT_MIN_TOKENS: int = 50

# If more than this fraction of chars are non-printable → gibberish
_MAX_GARBAGE_RATIO: float = 0.15

# Pattern: long runs of symbols / digits with no alphabetic characters
_SYMBOL_ONLY_RE = re.compile(r"^[^a-zA-Z]{50,}$")


class ChunkValidator:
    """Filters a list of RawChunks, discarding those that fail quality checks.

    Args:
        min_tokens: Minimum token count per chunk (default 50).
        remove_duplicates: When True (default), identical chunks are deduplicated.
    """

    def __init__(
        self,
        min_tokens: int = DEFAULT_MIN_TOKENS,
        remove_duplicates: bool = True,
    ) -> None:
        self.min_tokens = min_tokens
        self.remove_duplicates = remove_duplicates

    # ── Public API ────────────────────────────────────────────────────────────

    def validate_all(self, chunks: list[RawChunk]) -> list[RawChunk]:
        """Return only valid chunks from *chunks*.

        Preserves original ordering. If ``remove_duplicates`` is True,
        only the first occurrence of each normalised text is kept.
        """
        seen_texts: set[str] = set()
        valid: list[RawChunk] = []

        for chunk in chunks:
            reason = self._rejection_reason(chunk)
            if reason is not None:
                continue

            if self.remove_duplicates:
                key = self._normalise_key(chunk.text)
                if key in seen_texts:
                    continue
                seen_texts.add(key)

            valid.append(chunk)

        return valid

    def is_valid(self, chunk: RawChunk) -> bool:
        """Return True if *chunk* passes all quality checks."""
        return self._rejection_reason(chunk) is None

    def rejection_reason(self, chunk: RawChunk) -> str | None:
        """Return a human-readable rejection reason, or None if valid."""
        return self._rejection_reason(chunk)

    # ── Individual checks ─────────────────────────────────────────────────────

    def _rejection_reason(self, chunk: RawChunk) -> str | None:
        if not chunk.text:
            return "empty"
        if not chunk.text.strip():
            return "whitespace_only"
        token_count = chunk.token_count or count_tokens(chunk.text)
        if token_count < self.min_tokens:
            return f"too_short ({token_count} < {self.min_tokens} tokens)"
        if self._is_gibberish(chunk.text):
            return "gibberish"
        return None

    @staticmethod
    def _is_gibberish(text: str) -> bool:
        """Return True if *text* appears to be OCR garbage or binary noise."""
        if not text:
            return False
        # Count non-printable characters
        non_printable = sum(
            1 for ch in text if unicodedata.category(ch) in ("Cc", "Cf", "Cs")
        )
        if non_printable / max(len(text), 1) > _MAX_GARBAGE_RATIO:
            return True
        # Check for long runs of symbols with no alphabetic characters
        if _SYMBOL_ONLY_RE.match(text.strip()):
            return True
        return False

    @staticmethod
    def _normalise_key(text: str) -> str:
        """Normalise *text* for duplicate detection (case-fold, collapse spaces)."""
        return " ".join(text.lower().split())


# ── Module-level singleton ─────────────────────────────────────────────────────
chunk_validator = ChunkValidator()
