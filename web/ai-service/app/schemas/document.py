"""API response schemas for documents.

These are separate from the internal Document model:
  - DocumentSummary: used in list responses (no content — saves bandwidth).
  - DocumentDetail: used in upload and get-by-id responses (includes content).

Never return the internal Document model directly from a route; always project
through one of these schemas.
"""
from datetime import datetime
from typing import Any, Self

from pydantic import BaseModel

from app.models.document import Document


class DocumentSummary(BaseModel):
    """Lightweight projection returned in list endpoints."""

    document_id: str
    filename: str
    file_type: str
    mime_type: str
    page_count: int | None
    size_bytes: int
    word_count: int
    uploaded_by: str
    uploaded_at: datetime
    metadata: dict[str, Any]

    @classmethod
    def from_document(cls, doc: Document) -> Self:
        return cls(
            document_id=doc.document_id,
            filename=doc.filename,
            file_type=doc.file_type.value,
            mime_type=doc.mime_type,
            page_count=doc.page_count,
            size_bytes=doc.size_bytes,
            word_count=doc.metadata.get("word_count", 0),
            uploaded_by=doc.uploaded_by,
            uploaded_at=doc.uploaded_at,
            metadata=doc.metadata,
        )


class DocumentDetail(DocumentSummary):
    """Full projection including extracted content."""

    content: str
    content_length: int

    @classmethod
    def from_document(cls, doc: Document) -> "DocumentDetail":  # type: ignore[override]
        return cls(
            document_id=doc.document_id,
            filename=doc.filename,
            file_type=doc.file_type.value,
            mime_type=doc.mime_type,
            page_count=doc.page_count,
            size_bytes=doc.size_bytes,
            word_count=doc.metadata.get("word_count", 0),
            uploaded_by=doc.uploaded_by,
            uploaded_at=doc.uploaded_at,
            metadata=doc.metadata,
            content=doc.content,
            content_length=len(doc.content),
        )
