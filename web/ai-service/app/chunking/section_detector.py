"""Heading / section detector for the chunking pipeline.

Detects logical section boundaries in cleaned document text using a
prioritised set of regular-expression patterns. No NLP model is required.

Supported heading styles (in priority order):
  1. Markdown headings: ``# Title``, ``## Sub-title``
  2. ALL-CAPS lines: ``INTRODUCTION``, ``LEAVE POLICY``
  3. Numbered sections: ``1. Introduction``, ``2.1 Overview``
  4. Roman numeral sections: ``I. Introduction``, ``IV. Leave``
  5. Title-case short lines: ``Employee Benefits``
  6. Underlined headings (next line is ``===`` or ``---``)

False-positive filters reject lines that end with sentence-terminal
punctuation, look like dates, or contain only digits.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


# ── Heading patterns ──────────────────────────────────────────────────────────

# Each entry: (compiled_pattern, group_index_for_title)
_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    # Markdown: # Heading, ## Sub-heading (priority: highest)
    (re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE), 2),
    # ALL CAPS (min 3 chars, max 80, no lowercase): "LEAVE POLICY"
    (re.compile(r"^([A-Z][A-Z\s&/\(\)\-]{2,79})$", re.MULTILINE), 1),
    # Numbered: "1. Introduction", "2.1 Overview", "10.3.2 Appendix"
    (re.compile(r"^(\d+(?:\.\d+)*[.)]\s+[A-Z].{0,79})$", re.MULTILINE), 1),
    # Roman numerals: "I. Introduction", "IV. Benefits"
    (re.compile(r"^([IVXivx]{1,5}[.)]\s+[A-Z].{0,79})$", re.MULTILINE), 1),
    # Title-case short phrase (2–6 words, each capitalised): "Employee Benefits"
    (
        re.compile(
            r"^([A-Z][a-z]+(?:\s+(?:and|of|in|the|for|to|&|[A-Z][a-z]+)){1,5})$",
            re.MULTILINE,
        ),
        1,
    ),
]

# Underlined headings: "Title\n====" or "Title\n----"
_UNDERLINE_RE = re.compile(r"^([^\n]{3,80})\n[=\-]{3,}$", re.MULTILINE)

# Filters: patterns whose match should NOT be treated as a heading
_FALSE_POSITIVE_RES: list[re.Pattern[str]] = [
    re.compile(r"[.!?,:;]$"),           # sentence-terminal punctuation
    re.compile(r"^\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}$"),  # dates
    re.compile(r"^[\d\s.,]+$"),          # all numbers / punctuation
    re.compile(r"^\s*$"),               # blank
    re.compile(r"^[a-z]"),             # starts lowercase (body text)
]


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class DetectedSection:
    """A single heading found in the document."""

    start_pos: int
    """Character offset of the heading in the source text."""

    end_pos: int
    """Character offset of the end of the heading line (exclusive)."""

    title: str
    """Normalised heading text (Markdown ``#`` characters stripped)."""


# ── Detector ──────────────────────────────────────────────────────────────────

class SectionDetector:
    """Detects and assigns logical section headings to text blocks.

    Usage::

        detector = SectionDetector()
        blocks = detector.assign_sections(cleaned_text)
        # blocks: list[tuple[str, str]] → (text_block, section_title)
    """

    # ── Public API ────────────────────────────────────────────────────────────

    def detect(self, text: str) -> list[DetectedSection]:
        """Return all detected headings sorted by position in *text*."""
        candidates: dict[int, DetectedSection] = {}

        for pattern, title_group in _PATTERNS:
            for m in pattern.finditer(text):
                title = m.group(title_group).strip()
                # Strip Markdown # characters
                title = re.sub(r"^#+\s*", "", title)
                if not self._is_valid_heading(title):
                    continue
                pos = m.start()
                end = m.end()
                # Keep the heading if no heading yet at this position,
                # or if this one has a longer title (more specific).
                if pos not in candidates or len(title) > len(candidates[pos].title):
                    candidates[pos] = DetectedSection(
                        start_pos=pos, end_pos=end, title=title
                    )

        # Underlined headings
        for m in _UNDERLINE_RE.finditer(text):
            title = m.group(1).strip()
            if self._is_valid_heading(title):
                pos = m.start()
                if pos not in candidates:
                    candidates[pos] = DetectedSection(
                        start_pos=pos, end_pos=m.end(), title=title
                    )

        return sorted(candidates.values(), key=lambda s: s.start_pos)

    def assign_sections(self, text: str) -> list[tuple[str, str]]:
        """Split *text* by headings and return ``(block_text, section_title)`` pairs.

        The first block (before the first heading) is assigned section title
        ``""`` unless no headings are found at all, in which case the entire
        text is returned as a single block with section ``""``.

        Args:
            text: Cleaned document text.

        Returns:
            Ordered list of ``(text_block, section_title)`` tuples.
            Empty blocks (after stripping) are excluded.
        """
        headings = self.detect(text)
        if not headings:
            return [(text, "")] if text.strip() else []

        result: list[tuple[str, str]] = []
        prev_end = 0
        prev_title = ""

        for heading in headings:
            block = text[prev_end : heading.start_pos].strip()
            if block:
                result.append((block, prev_title))
            prev_title = heading.title
            # Advance past the entire heading (and its underline, if present)
            prev_end = heading.end_pos
            # Skip any immediately following blank line
            while prev_end < len(text) and text[prev_end] in ("\n", "\r"):
                prev_end += 1

        # Trailing block after the last heading
        tail = text[prev_end:].strip()
        if tail:
            result.append((tail, prev_title))

        return result

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _is_valid_heading(title: str) -> bool:
        """Return False if *title* looks like body text rather than a heading."""
        if len(title) < 3 or len(title) > 120:
            return False
        for fp in _FALSE_POSITIVE_RES:
            if fp.search(title):
                return False
        return True


# ── Module-level singleton ─────────────────────────────────────────────────────
section_detector = SectionDetector()
