"""EmbeddedChunk model — vector representation of a Chunk.

The embedding is kept separate from the Chunk so that:
  * Chunks can be re-embedded with a different model without altering chunk data.
  * The two stores can be scaled independently (Increment 6: Chroma).
  * Tests can validate chunking without needing an embedding provider.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EmbeddedChunk(BaseModel):
    """A Chunk paired with its embedding vector."""

    embedded_id: str = Field(default_factory=lambda: str(uuid4()))
    """Unique ID for this embedding record."""

    chunk_id: str
    """ID of the source Chunk (``<doc_short>_chunk<NNNN>``)."""

    document_id: str
    """ID of the parent Document."""

    embedding: list[float]
    """Dense vector produced by the embedding model."""

    dimensions: int
    """Length of the embedding vector (e.g. 1536 for text-embedding-3-small)."""

    provider: str
    """Embedding provider name: ``openai``, ``voyage``, ``local``, …"""

    model: str
    """Model identifier (e.g. ``text-embedding-3-small``)."""

    token_count: int = 0
    """Token count of the source chunk text."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    """Metadata inherited from the source Chunk (filename, section, …)."""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
