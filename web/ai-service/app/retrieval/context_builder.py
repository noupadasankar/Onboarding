"""Context builder — merges reranked chunks into a single coherent context string.

Design decisions:
  * Results are ordered by rank (lowest = highest relevance).
  * Duplicate chunk IDs are skipped.
  * A section header is prepended per chunk when the section differs from the previous.
  * The builder respects a token budget: once adding the next chunk would exceed
    ``max_tokens``, it stops (never splits a chunk in half).
  * Token counting uses tiktoken when available, falling back to len ÷ 4.

Usage::

    builder = ContextBuilder(max_tokens=4000)
    context, token_count = builder.build(search_results)
"""
from __future__ import annotations

from app.chunking.token_chunker import count_tokens
from app.models.search_result import SearchResult

_CHUNK_SEPARATOR = "\n\n---\n\n"
_SECTION_HEADER = "## {section}\n"


class ContextBuilder:
    """Assembles a context string from a list of SearchResult objects.

    Args:
        max_tokens: Maximum tokens for the assembled context.
            Defaults to 6000 (leaves ~2000 for system prompt + question with
            gpt-4o's 8192 context window, or much more with Claude).
        include_metadata: If True, prepend a one-line metadata header to each chunk.
    """

    def __init__(
        self,
        max_tokens: int = 6_000,
        include_metadata: bool = True,
    ) -> None:
        self.max_tokens = max_tokens
        self.include_metadata = include_metadata

    def build(self, results: list[SearchResult]) -> tuple[str, int]:
        """Build the context string.

        Args:
            results: Reranked SearchResult list (rank 0 = most relevant).

        Returns:
            Tuple of (context_text, total_token_count).
        """
        if not results:
            return "", 0

        parts: list[str] = []
        seen_ids: set[str] = set()
        total_tokens = 0
        prev_section = ""

        for r in results:
            if r.chunk_id in seen_ids:
                continue
            seen_ids.add(r.chunk_id)

            chunk_text = self._format_chunk(r, prev_section)
            chunk_tokens = count_tokens(chunk_text)

            if total_tokens + chunk_tokens > self.max_tokens and parts:
                # Budget exhausted — stop; never split mid-chunk
                break

            parts.append(chunk_text)
            total_tokens += chunk_tokens
            prev_section = r.section or ""

        context = _CHUNK_SEPARATOR.join(parts)
        return context, total_tokens

    def _format_chunk(self, r: SearchResult, prev_section: str) -> str:
        lines: list[str] = []

        if self.include_metadata:
            meta_parts = []
            if r.filename:
                meta_parts.append(r.filename)
            if r.page is not None and r.page > 0:
                meta_parts.append(f"p.{r.page}")
            if r.section and r.section != prev_section:
                meta_parts.append(r.section)
            if meta_parts:
                lines.append(f"[{' | '.join(meta_parts)}]")

        lines.append(r.text)
        return "\n".join(lines)
