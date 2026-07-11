"""Unified Chunk model.

Every component of the chunking pipeline (cleaner, section detector,
token chunker, validator) ultimately produces or consumes Chunk objects.
This model is the contract between the ingestion pipeline (Increment 4)
and the embedding pipeline (Increment 5).

Never expose this model directly as an API response; project through the
schemas in app/schemas/chunk.py.
"""
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """A single text chunk derived from a Document."""

    chunk_id: str
    """Stable identifier: ``<doc_short_id>_chunk<NNNN>``.

    Example: ``a3f9b201_chunk0001``
    """

    document_id: str
    """ID of the parent Document this chunk was extracted from."""

    chunk_index: int
    """0-based position of this chunk within the document's chunk list."""

    text: str
    """Cleaned, ready-to-embed text content of this chunk."""

    token_count: int
    """Number of tokens in *text* (tiktoken cl100k_base, or approximation)."""

    page: int | None = None
    """Source page number, if determinable from the document format."""

    section: str | None = None
    """Heading of the logical section this chunk belongs to (may be empty)."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    """Metadata inherited from the parent Document plus chunk-specific fields."""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @classmethod
    def build_id(cls, document_id: str, index: int) -> str:
        """Generate a stable, human-readable chunk ID.

        Args:
            document_id: UUID of the parent document.
            index: 0-based chunk index.

        Returns:
            e.g. ``a3f9b201_chunk0001``
        """
        short = document_id.replace("-", "")[:8]
        return f"{short}_chunk{index:04d}"
