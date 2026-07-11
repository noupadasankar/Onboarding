"""Text cleaning service for the chunking pipeline.

Raw document text — whether from PDFs, DOCX files, or CSVs — almost
always contains noise that degrades retrieval quality:

  - Invisible Unicode control characters
  - Repeated page headers and footers (OCR / PDF extraction artefacts)
  - Inconsistent quotation marks and bullet characters
  - Hyphenated line-break joins (OCR artefact)
  - Multiple consecutive blank lines or stray whitespace

This module removes that noise without altering the semantic content of
the document. The clean() method is idempotent.
"""
import re
import unicodedata
from collections import Counter

# ── Unicode normalisation tables ──────────────────────────────────────────────

# Control characters and invisible formatting characters
_INVISIBLE_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f"
    r"­"           # soft hyphen
    r"​-‏"    # zero-width spaces / bidi marks
    r"‪-‮"    # bidi embedding / override
    r"⁠-⁯"    # word joiner, invisible math operators, etc.
    r"﻿"           # byte-order mark (BOM)
    r"￹-￿"    # interlinear annotation, specials
    r"]"
)

# Fancy / curly quotation marks → straight equivalents
_QUOTE_TABLE = str.maketrans(
    {
        "‘": "'",   # left single quotation mark
        "’": "'",   # right single quotation mark (also apostrophe)
        "‚": "'",   # single low-9 quotation mark
        "‛": "'",   # single high-reversed-9 quotation mark
        "“": '"',   # left double quotation mark
        "”": '"',   # right double quotation mark
        "„": '"',   # double low-9 quotation mark
        "‟": '"',   # double high-reversed-9 quotation mark
        "‹": "'",   # single left-pointing angle quotation mark
        "›": "'",   # single right-pointing angle quotation mark
        "«": '"',   # left-pointing double angle quotation mark «
        "»": '"',   # right-pointing double angle quotation mark »
    }
)

# Fancy bullet characters → ASCII hyphen
_BULLET_TABLE = str.maketrans(
    {
        "•": "-",   # bullet •
        "‣": "-",   # triangular bullet ‣
        "⁃": "-",   # hyphen bullet ⁃
        "■": "-",   # black square ■
        "▪": "-",   # black small square ▪
        "▸": "-",   # black right-pointing small triangle ▸
        "●": "-",   # black circle ●
        "⚬": "-",   # medium small white circle ⚬
        "․": ".",   # one dot leader ․
    }
)

# Fancy dashes → ASCII equivalents
_DASH_TABLE = str.maketrans(
    {
        "–": "-",      # en dash –
        "—": " - ",    # em dash — (spaced)
        "―": " - ",    # horizontal bar ―
        "−": "-",      # minus sign −
        "‐": "-",      # non-breaking hyphen
        "‑": "-",      # non-breaking hyphen
    }
)

# Hyphenated line-break join: "hyphen-\nated" → "hyphenated"
_HYPHEN_BREAK_RE = re.compile(r"(\w)-\n(\w)")

# Multiple consecutive spaces / tabs → single space (within a line)
_MULTI_SPACE_RE = re.compile(r"[ \t]+")

# Three or more consecutive blank lines → one blank line
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


class TextCleaner:
    """Cleans raw document text before it enters the chunking pipeline.

    All cleaning operations are collected in :meth:`clean`, which applies
    them in a deterministic order. Each private method is independently
    testable.

    Args:
        repeated_line_threshold: A line that appears at least this many
            times in the document is considered a repeating header/footer
            and removed (after the first occurrence). Default: 3.
    """

    def __init__(self, repeated_line_threshold: int = 3) -> None:
        self._threshold = repeated_line_threshold

    # ── Public API ────────────────────────────────────────────────────────────

    def clean(self, text: str) -> str:
        """Return a cleaned copy of *text*.

        Operations (in order):
          1. Normalise line endings to LF.
          2. Strip invisible Unicode characters.
          3. Join OCR-hyphenated line breaks.
          4. Normalise quotation marks, bullets, and dashes.
          5. Remove repeated page headers / footers.
          6. Collapse excessive whitespace and blank lines.
          7. Strip leading/trailing whitespace.

        The input is never mutated.
        """
        if not text:
            return ""

        text = self._normalize_line_endings(text)
        text = self._remove_invisible(text)
        text = self._join_hyphen_breaks(text)
        text = self._normalize_quotes(text)
        text = self._normalize_bullets(text)
        text = self._normalize_dashes(text)
        text = self._remove_repeated_lines(text)
        text = self._normalize_whitespace(text)
        return text.strip()

    # ── Individual cleaning steps ─────────────────────────────────────────────

    @staticmethod
    def _normalize_line_endings(text: str) -> str:
        return text.replace("\r\n", "\n").replace("\r", "\n")

    @staticmethod
    def _remove_invisible(text: str) -> str:
        text = _INVISIBLE_RE.sub("", text)
        return unicodedata.normalize("NFC", text)

    @staticmethod
    def _join_hyphen_breaks(text: str) -> str:
        """Re-join words broken across lines by a trailing hyphen."""
        return _HYPHEN_BREAK_RE.sub(r"\1\2", text)

    @staticmethod
    def _normalize_quotes(text: str) -> str:
        return text.translate(_QUOTE_TABLE)

    @staticmethod
    def _normalize_bullets(text: str) -> str:
        return text.translate(_BULLET_TABLE)

    @staticmethod
    def _normalize_dashes(text: str) -> str:
        return text.translate(_DASH_TABLE)

    def _remove_repeated_lines(self, text: str) -> str:
        """Remove lines that appear >= threshold times (likely headers/footers).

        Only short lines (≤ 100 chars) qualify as candidates to avoid
        accidentally removing repeated paragraphs.
        """
        lines = text.split("\n")
        # Count stripped non-empty short lines
        freq: Counter[str] = Counter(
            ln.strip()
            for ln in lines
            if ln.strip() and len(ln.strip()) <= 100
        )
        repeated: set[str] = {
            ln for ln, count in freq.items() if count >= self._threshold
        }
        if not repeated:
            return text

        seen: set[str] = set()
        result: list[str] = []
        for ln in lines:
            stripped = ln.strip()
            if stripped in repeated:
                if stripped not in seen:
                    seen.add(stripped)
                    result.append(ln)
                # else: silently drop subsequent occurrences
            else:
                result.append(ln)
        return "\n".join(result)

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Collapse multiple spaces/tabs within lines; limit blank lines to one."""
        lines = text.split("\n")
        cleaned: list[str] = []
        blank_run = 0
        for ln in lines:
            ln = _MULTI_SPACE_RE.sub(" ", ln).rstrip()
            if not ln.strip():
                blank_run += 1
                if blank_run == 1:
                    cleaned.append("")
            else:
                blank_run = 0
                cleaned.append(ln)
        # Remove leading/trailing blank lines from the result list
        while cleaned and not cleaned[0]:
            cleaned.pop(0)
        while cleaned and not cleaned[-1]:
            cleaned.pop()
        return "\n".join(cleaned)


# ── Module-level singleton ─────────────────────────────────────────────────────
text_cleaner = TextCleaner()
