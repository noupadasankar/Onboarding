"""Query processor — normalises raw user input before embedding.

Never send raw user text directly to the embedding model.

Normalisations applied (in order):
  1. Strip leading / trailing whitespace.
  2. Collapse internal whitespace runs to a single space.
  3. Unicode NFKC normalisation (e.g. full-width → ASCII, ligatures).
  4. Strip repeated punctuation at sentence end (??? → ?, !!! → !).
  5. Enforce a minimum and maximum length guard.

The normalised query preserves meaning — it does NOT stem, lemmatise,
or remove stop-words (those would hurt semantic embedding quality).
"""
from __future__ import annotations

import re
import unicodedata

_MAX_QUERY_LEN = 1_000   # chars — safety cap before embedding
_MIN_QUERY_LEN = 2       # chars — below this we reject


class QueryProcessingError(ValueError):
    """Raised when a query cannot be normalised (empty, too long, etc.)."""


class QueryProcessor:
    """Normalise a raw user query string for embedding.

    Usage::

        processor = QueryProcessor()
        clean = processor.process("  How many annual leaves do I get???   ")
        # → "How many annual leaves do I get?"
    """

    def __init__(
        self,
        max_length: int = _MAX_QUERY_LEN,
        min_length: int = _MIN_QUERY_LEN,
    ) -> None:
        self.max_length = max_length
        self.min_length = min_length

    def process(self, raw: str) -> str:
        """Return a normalised query string.

        Raises:
            QueryProcessingError: If the query is empty or too long after normalisation.
        """
        if not isinstance(raw, str):
            raise QueryProcessingError("Query must be a string.")

        # 1. Unicode NFKC
        text = unicodedata.normalize("NFKC", raw)

        # 2. Strip surrounding whitespace
        text = text.strip()

        # 3. Collapse internal whitespace
        text = re.sub(r"[ \t\r\n]+", " ", text)

        # 4. Deduplicate trailing punctuation  ??? → ?   !!! → !   ... stays
        text = re.sub(r"([?!])\1+", r"\1", text)

        # 5. Length guards
        if len(text) < self.min_length:
            raise QueryProcessingError(
                f"Query is too short after normalisation (got {len(text)} chars, "
                f"minimum {self.min_length})."
            )
        if len(text) > self.max_length:
            raise QueryProcessingError(
                f"Query is too long ({len(text)} chars, maximum {self.max_length})."
            )

        return text


# Module-level singleton
query_processor = QueryProcessor()
