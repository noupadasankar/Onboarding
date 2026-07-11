"""API response schemas for chunking.

Separate from the internal Chunk model so that the API contract
is stable even as the internal model evolves.
"""
from pydantic import BaseModel


class ProcessingSummary(BaseModel):
    """Returned by POST /documents/{id}/process."""

    success: bool = True
    document_id: str
    filename: str
    chunks_created: int
    total_tokens: int
    average_tokens: float
    largest_chunk: int
    smallest_chunk: int

    @classmethod
    def from_chunks(
        cls,
        document_id: str,
        filename: str,
        chunks: list,
    ) -> "ProcessingSummary":
        """Build a summary from a list of :class:`~app.models.chunk.Chunk` objects."""
        if not chunks:
            return cls(
                document_id=document_id,
                filename=filename,
                chunks_created=0,
                total_tokens=0,
                average_tokens=0.0,
                largest_chunk=0,
                smallest_chunk=0,
            )
        token_counts = [c.token_count for c in chunks]
        total = sum(token_counts)
        return cls(
            document_id=document_id,
            filename=filename,
            chunks_created=len(chunks),
            total_tokens=total,
            average_tokens=round(total / len(chunks), 1),
            largest_chunk=max(token_counts),
            smallest_chunk=min(token_counts),
        )


class ChunkResponse(BaseModel):
    """Lightweight representation of a single chunk (for list/inspect endpoints)."""

    chunk_id: str
    chunk_index: int
    section: str | None
    page: int | None
    token_count: int
    text_preview: str
    """First 200 characters of the chunk text."""

    @classmethod
    def from_chunk(cls, chunk: object) -> "ChunkResponse":
        from app.models.chunk import Chunk  # avoid circular import

        c: Chunk = chunk  # type: ignore[assignment]
        return cls(
            chunk_id=c.chunk_id,
            chunk_index=c.chunk_index,
            section=c.section,
            page=c.page,
            token_count=c.token_count,
            text_preview=c.text[:200],
        )
