"""VectorDocument model — the shape of data stored in and retrieved from ChromaDB.

This is the transfer object between the vector repository and the vector service.
It is not the EmbeddedChunk (Increment 5 internal) — it is the canonical
representation of a persisted vector record.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class VectorDocument(BaseModel):
    """A single record as stored in ChromaDB."""

    chunk_id: str
    """ChromaDB document ID (unique per collection)."""

    document_id: str
    """Parent document UUID — used to delete all chunks of a document."""

    embedding: list[float]
    """Dense vector (provider-generated)."""

    text: str
    """The chunk text (stored as ChromaDB document content)."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    """Flat key→scalar metadata dict (ChromaDB requirement: no nested objects)."""

    indexed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class VectorSearchResult(BaseModel):
    """A single result returned by a similarity search."""

    chunk_id: str
    document_id: str
    text: str
    score: float
    """Cosine similarity or distance score (provider-dependent)."""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CollectionStats(BaseModel):
    """Statistics for a ChromaDB collection."""

    collection_name: str
    total_chunks: int
    unique_documents: int
    embedding_model: str = ""
    embedding_dimensions: int = 0
